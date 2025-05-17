local modem_side = "back" 
local output_side = "left" 

if not peripheral.find("modem", function(name, p) return p.isWireless() end) then
    print("Error: No wireless modem found. Please attach one.")
    return
end

rednet.open(modem_side)
local my_id = os.getComputerID()
print("Peripheral ID: " .. my_id .. " listening for commands.")
print("Device output on side: " .. output_side)

while true do
    local senderID, message, protocol = rednet.receive()
    if message then
        print("Received command: '" .. message .. "' from ID: " .. senderID)
        if message == "turn_on" or message == "lock" then
            print("Activating redstone on side: " .. output_side)
            redstone.setOutput(output_side, true)
        elseif message == "turn_off" or message == "unlock" then
            print("Deactivating redstone on side: " .. output_side)
            redstone.setOutput(output_side, false)
        else
            print("Unknown command: " .. message)
        end
    end
end