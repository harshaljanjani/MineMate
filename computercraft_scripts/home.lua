local peripheral_config = {}
local config_file_path = "peripheral_config.txt"
local modem_side = "back"
local nestjs_server_url = "http://127.0.0.1:3000" 

local function load_peripheral_config()
    peripheral_config = {}
    if fs.exists(config_file_path) then
        local file = fs.open(config_file_path, "r")
        if file then
            print("Reading " .. config_file_path .. "...")
            local line_num = 0
            local parse_errors = 0
            while true do
                local line = file.readLine()
                if line == nil then break end
                line_num = line_num + 1
                line = line:match("^%s*(.-)%s*$")
                if line ~= "" and not line:match("^#") then
                    local eq_pos = line:find("=", 1, true)
                    if eq_pos then
                        local key = line:sub(1, eq_pos - 1):match("^%s*(.-)%s*$")
                        local value_str = line:sub(eq_pos + 1):match("^%s*(.-)%s*$")
                        local value_num = tonumber(value_str)
                        if key ~= "" and value_num ~= nil then
                            peripheral_config[key] = value_num
                        else
                            print("Error parsing line " .. line_num .. " in " .. config_file_path .. ": '" .. line .. "'. Invalid key or non-numeric value.")
                            parse_errors = parse_errors + 1
                        end
                    else
                        print("Error parsing line " .. line_num .. " in " .. config_file_path .. ": '" .. line .. "'. Expected 'key=value' format.")
                        parse_errors = parse_errors + 1
                    end
                end
            end
            file.close()
            if parse_errors == 0 and line_num > 0 then
                print("Peripheral configuration loaded successfully from " .. config_file_path .. ".")
            elseif parse_errors > 0 then
                print("Found " .. parse_errors .. " error(s) while parsing " .. config_file_path .. ". Some configurations might be missing.")
            else
                print(config_file_path .. " was empty or only contained comments. Using empty config.")
            end
        else
            print("Error: Could not open " .. config_file_path .. ". Using empty config.")
        end
    else
        print("Warning: " .. config_file_path .. " not found. Peripheral control will be limited.")
    end
end

load_peripheral_config()
if not peripheral.find("modem", function(name, p) return p.isWireless() end) then
    print("Error: No wireless modem found on this computer. Please attach one.")
    return
end
rednet.open(modem_side)
print("Central hub ID: " .. os.getComputerID() .. " using modem on side: " .. modem_side)

print("===== HTTP CONFIG START =====")
print("Checking 'http' API availability...")
if http == nil then
    print("FATAL: The 'http' global API table is nil. HTTP API is likely disabled or not loaded.")
    print("Please ensure 'http.enabled = true' in your computercraft_server.toml and restart Minecraft.")
elseif type(http) ~= "table" then
    print("FATAL: The 'http' global is not a table. Type is: " .. type(http) .. ". This is unexpected.")
else
    print("'http' global API table is present.")
end
print("===== HTTP CONFIG END =====")

local websocket_url = "ws://127.0.0.1:3000"
print("Attempting to connect to WebSocket server at: " .. websocket_url)

local ws, err = http.websocket(websocket_url)
if ws then
    print("WebSocket connected successfully!")
else
    print("WebSocket connection failed!")
    print("Error: " .. tostring(err))
end

if ws then
    ws.onMessage = function(payload_str, isBinary)
        local old_x, old_y = term.getCursorPos()
        term.setCursorPos(1, term.getCursorPos())
        term.clearLine()

        if isBinary then
            print("Received binary WebSocket message, ignoring.")
        else
            print("Raw WebSocket payload: " .. payload_str)
            local success, event_data = pcall(textutils.unserializeJSON, payload_str)

            if not success or type(event_data) ~= "table" or type(event_data.type) ~= "string" or event_data.payload == nil then
                print("Error: Malformed WebSocket message or failed to parse JSON: " .. (tostring(event_data) or "parse error"))
                print("Original payload: " .. payload_str)
            else
                local event_type = event_data.type
                local message_content = event_data.payload

                if event_type == "command" then
                    print("Received command to relay: " .. message_content)
                    local parts = {}
                    for part in message_content:gmatch("%S+") do
                        table.insert(parts, part)
                    end
                    if #parts == 3 then
                        local action, device, room_identifier = parts[1], parts[2], parts[3]
                        local config_key = device:lower() .. "_" .. room_identifier:lower()
                        local target_peripheral_id = peripheral_config[config_key]
                        if target_peripheral_id then
                            print("Relaying action '" .. action .. "' to peripheral ID " .. target_peripheral_id .. " for " .. device .. " (" .. room_identifier .. ").")
                            local rednet_ok, rednet_err_msg = rednet.send(target_peripheral_id, action)
                            if not rednet_ok then
                                print("Failed to send rednet message: " .. (rednet_err_msg or "unknown error"))
                            end
                        else
                            print("Error: No peripheral configured for " .. device .. " (" .. room_identifier .. ") with key: '" .. config_key .. "'.")
                        end
                    else
                        print("Invalid command format from server: " .. message_content)
                    end
                elseif event_type == "sequence_command" then
                    local sequence_data = textutils.unserializeJSON(message_content)
                    if type(sequence_data) == "table" and type(sequence_data.commands) == "table" and (type(sequence_data["repeat"]) == "number" or sequence_data["repeat"] == "infinite") then
                        local repeat_count = sequence_data["repeat"] == "infinite" and 1000 or sequence_data["repeat"]
                        local delay_ms = sequence_data.delay_ms or 0
                        for i = 1, repeat_count do
                            for _, cmd in ipairs(sequence_data.commands) do
                                if type(cmd) == "table" and cmd.action and cmd.device and cmd.room then
                                    local config_key = cmd.device:lower() .. "_" .. cmd.room:lower()
                                    local target_peripheral_id = peripheral_config[config_key]
                                    if target_peripheral_id then
                                        print("Executing action '" .. cmd.action .. "' on peripheral ID " .. target_peripheral_id .. " for " .. cmd.device .. " (" .. cmd.room .. ").")
                                        rednet.send(target_peripheral_id, cmd.action)
                                    else
                                        print("Error: No peripheral configured for " .. cmd.device .. " (" .. cmd.room .. ") with key: '" .. config_key .. "'.")
                                    end
                                else
                                    print("Invalid command in sequence: " .. textutils.serialize(cmd))
                                end
                            end
                            if i < repeat_count and delay_ms > 0 then
                                sleep(delay_ms / 1000)
                            end
                        end
                    else
                        print("Invalid sequence_command payload: " .. message_content)
                    end
                elseif event_type == "info" then
                    print("Info from Server: " .. message_content)
                else
                    print("Unknown WebSocket event type received: " .. event_type)
                end
            end
        end
        term.write("Type in your prompt! > ")
        term.setCursorPos(old_x, old_y)
    end

    ws.onClose = function(code, reason)
        local old_x, old_y = term.getCursorPos()
        term.setCursorPos(1, term.getCursorPos())
        term.clearLine()
        print("WebSocket connection closed. Code: " .. tostring(code) .. ", Reason: " .. tostring(reason))
        ws = nil
        term.write("Type in your prompt! > ")
        term.setCursorPos(old_x, old_y)
    end

    ws.onError = function(error_message)
        local old_x, old_y = term.getCursorPos()
        term.setCursorPos(1, term.getCursorPos())
        term.clearLine()
        print("WebSocket error: " .. tostring(error_message))
        ws = nil
        term.write("Type in your prompt! > ")
        term.setCursorPos(old_x, old_y)
    end
end

if not ws then
    print("WebSocket Connection FAILED!")
    print("Error message from http.websocket: " .. tostring(err))
    print(" ")
    print("Attempting a simple HTTP GET to the base NestJS server (" .. nestjs_server_url .. ") to check basic connectivity.")
    local handle_http, err_http = http.request(nestjs_server_url)
    if handle_http then
        if type(handle_http) == "table" and handle_http.readAll then
            print("HTTP GET to " .. nestjs_server_url .. " was SUCCESSFUL (got a response handle). Reading response...")
            local response_content = handle_http.readAll()
            print("Response (first 100 chars): " .. string.sub(tostring(response_content or "N/A"), 1, 100))
            handle_http.close()
            print("If you see HTML or 'Cannot GET /', basic HTTP to 127.0.0.1:3000 is likely allowed.")
            print("The issue might be specific to WebSockets (http.websocket_enabled in .toml?) or the ws:// protocol.")
        else
            print("HTTP GET to " .. nestjs_server_url .. " was INITIATED, but did not return a standard response handle. Got type: " .. type(handle_http) .. ". Error (if any): " .. tostring(err_http))
        end
    else
        print("HTTP GET to " .. nestjs_server_url .. " also FAILED. Error: " .. tostring(err_http))
        print("This suggests a more general problem reaching " .. nestjs_server_url .. " from ComputerCraft, or http.enabled is false, or rules in .toml are blocking all access.")
    end
    print("Troubleshooting: Ensure '127.0.0.1' or '127.0.0.1/8' is in computercraft_server.toml [[http.rules]] with action = 'allow'. Also check http.enabled and http.websocket_enabled are true. Restart Minecraft after .toml changes.")
    print("Continuing without WebSocket for server-pushed commands. Interactive mode will use HTTP POST.")
end

local function send_command_to_model(user_command)
    local api_url = nestjs_server_url .. "/command"
    local payload = textutils.serializeJSON({ command = user_command })
    if not payload then
        print("Error: Could not serialize command to JSON.")
        return
    end
    local handle, err_post, headers_response = http.post(api_url, payload, { ["Content-Type"] = "application/json" })

    if not handle then
        print("Error sending command to model: " .. tostring(err_post))
        if headers_response then
            print("Response headers from failed request:")
            for k,v in pairs(headers_response) do
                print(k .. ": " .. tostring(v))
            end
        end
        return
    end

    local response_body = handle.readAll()
    handle.close()

    if response_body == nil or response_body == "" then
        print("Error: Received empty response from model backend.")
        return
    end

    local success, response_data = pcall(textutils.unserializeJSON, response_body)
    if not success or type(response_data) ~= "table" then
        print("Error parsing model response JSON: " .. tostring(response_data or "parse error"))
        print("Raw response: " .. response_body)
        return
    end

    local display_text = ""
    if response_data.raw_response then
        display_text = response_data.raw_response
        if response_data.action_details then
            local json_start_index = display_text:find("{", 1, true)
            if json_start_index then
                display_text = display_text:sub(1, json_start_index - 1)
            end
        end
        display_text = display_text:match("^%s*(.-)%s*$")
    end

    if display_text and display_text ~= "" then
        local unwrapped_multiline = display_text:match("^```%w*%s*\n(.-)\n```$")
        if unwrapped_multiline then
            display_text = unwrapped_multiline
        else
            local unwrapped_singleline = display_text:match("^```%w*%s*(.-)```$")
            if unwrapped_singleline then
                display_text = unwrapped_singleline
            else
                display_text = display_text:gsub("%s*```%w*%s*$", "")
            end
        end
        display_text = display_text:match("^%s*(.-)%s*$")
    end

    if display_text ~= "" then
        print("Model > " .. display_text)
    else
        print("Model > (No displayable response)")
    end

    if response_data.action_details then
        if type(response_data.action_details) == "table" then
            if response_data.action_details.commands then
                local sequence_data = response_data.action_details
                local repeat_count = sequence_data["repeat"] == "infinite" and 1000 or sequence_data["repeat"]
                local delay_ms = sequence_data.delay_ms or 0
                for i = 1, repeat_count do
                    for _, cmd in ipairs(sequence_data.commands) do
                        if type(cmd) == "table" and cmd.action and cmd.device and cmd.room then
                            local config_key = cmd.device:lower() .. "_" .. cmd.room:lower()
                            local target_peripheral_id = peripheral_config[config_key]
                            if target_peripheral_id then
                                print("Executing action '" .. cmd.action .. "' on peripheral ID " .. target_peripheral_id .. " for " .. cmd.device .. " (" .. cmd.room .. ").")
                                rednet.send(target_peripheral_id, cmd.action)
                            else
                                print("Error: No peripheral configured for " .. cmd.device .. " (" .. cmd.room .. ") with key: '" .. config_key .. "'.")
                            end
                        else
                            print("Invalid command in sequence: " .. textutils.serialize(cmd))
                        end
                    end
                    if i < repeat_count and delay_ms > 0 then
                        sleep(delay_ms / 1000)
                    end
                end
            elseif response_data.action_details.action and response_data.action_details.device and response_data.action_details.room then
                local ad = response_data.action_details
                local config_key = ad.device:lower() .. "_" .. ad.room:lower()
                local target_peripheral_id = peripheral_config[config_key]
                if target_peripheral_id then
                    local rednet_success, rednet_err = rednet.send(target_peripheral_id, ad.action)
                    if not rednet_success then
                        print("Failed to send rednet command: " .. (rednet_err or "unknown error"))
                    end
                else
                    print("Error: No peripheral configured for " .. ad.device .. " (" .. ad.room .. ") with key: '" .. config_key .. "'.")
                end
            else
                print("Unrecognized action_details structure.")
            end
        else
            print("action_details is not a table.")
        end
    end
    if response_data.error then
        print("Error from model system: " .. response_data.error)
    end
end

term.clear()
term.setCursorPos(1,1)
print("==========================================")
print("   __  ____          __  ___     __     ")
print("  /  |/  (_)__  ___ /  |/  /__ _/ /____ ")
print(" / /|_/ / / _ \\/ -_) /|_/ / _ `/ __/ -_)")
print("/_/  /_/_/_//_/\\__/_/  /_/\\_,_/\\__/\\__/ ")
print("                                        ")
print("==========================================")
print("Command Interface. Type 'EXIT' to quit.")
print("==========================================")

while true do
    term.write("Type in your prompt! > ")
    local input = read()
    if not input then
        print("\nInput stream closed. Exiting.")
        break
    end
    if input:upper() == "EXIT" then
        break
    elseif input:match("^%s*$") then
    else
        send_command_to_model(input)
    end
end

if ws then
    ws.close()
end
print("\nAdiós! Happy to be of service!")