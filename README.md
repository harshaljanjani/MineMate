# MineMate: Because Mining Is More Enjoyable When It’s Not Just Mine

MineMate enables you to use natural language to control in-game devices in Minecraft through the Gemma using the Google GenAI SDK with a Python FastAPI backend
processes commands, a NestJS server enables MQTT brokerage over WebSockets/HTTP, and ComputerCraft scripts perform in-game execution. I've actually tested it locally with "Tekkit: The Ressurection," but the devices I've used in the demo apply generally to the ComputerCraft modpack too. You can find the [video demonstration](https://drive.google.com/file/d/16RfNWLFXnLSdoitsg-IkZCFiyUxlABo-/view?usp=sharing) linked here as well.

![Booting into MineMate - Your Minecraft Assistant Awaits](https://github.com/user-attachments/assets/42b94d3e-1cdc-465a-a300-648143c3f6b7)

**Please bear in mind:** This add-on is not "magic," but is intended as an example to demonstrate to you how you might incorporate your favorite models into Minecraft. During its early and simple form, the library is very dependent on changes made to repository files by developers in order to customize the repository to their specific application, but changes would be small relative to the repository as a whole.

## Requirements

* Python 3.7
* Node.js (recommended version is LTS)
* npm
* NestJS
* Pydantic
* Minecraft Java Edition with Tekkit: The Resurrection/ComputerCraft (CC: Tweaked) modification
* Google AI Studio API Key (as `GEMMA_API_KEY` environment variable)
* Git

## Overview

1. **Clone the Repository**

   ```bash
   git clone https://github.com  
   cd MineMate  
   ```

2. **Python Backend**

   * Set the API key:

     * Linux/macOS: `export GEMMA_API_KEY="YOUR_API_KEY_GOES_HERE"`
     * Windows (PowerShell): `$env:GEMMA_API_KEY="YOUR_API_KEY_GOES_HERE"`
     * Windows (CMD): `set GEMMA_API_KEY=YOUR_API_KEY_GOES_HERE"`
   * It is advisable to create a virtual setup in order to install dependencies independent of your local setup:

     ```bash
     python -m venv venv  
     source venv/bin/activate  # Windows: venv/Scripts/activate  
     ```
   * Run:

     ```bash
     uvicorn app:app --reload --port 8000
     # Initializes the FastAPI server to handle interactions with the model.
     ```

3. **NestJS Server**

   ```bash
   cd nestjs_server  
   npm install  
   npm run start:dev  
   cd ..  
   ```

4. **ComputerCraft Setup**

   * Copy `computercraft_scripts/home.lua` to a `home` program on the main hub computer.
   * Copy `computercraft_scripts/generic_peripheral_controller.lua` to peripheral computers.
   * Copy `computercraft_scripts/peripheral_config.txt` to the root of the hub computer.
   * Enable HTTP/WebSocket in `config/computercraft_server.toml` by removing any rules listed **before** the following entry under `[[http.rules]]`:

     ```toml
     http.enabled = true  
     http.websocket_enabled = true  

     #The host may be a domain name ("pastebin.com"), wildcard ("*.pastebin.com") or
	 #CIDR notation ("127.0.0.0/8").
	 #If no rules, the domain is blocked.
	 [[http.rules]]
		#The maximum size (in bytes) that a computer can send or receive in one websocket packet.
		max_websocket_message = 131072
		host = "*"
		#The maximum size (in bytes) that a computer can upload in a single request. This
		#includes headers and POST text.
		max_upload = 4194304
		action = "allow"
		#The maximum size (in bytes) that a computer can download in a single request.
		#Note that responses may receive more data than allowed, but this data will not
		#be returned to the client.
		max_download = 16777216
		#The period of time (in milliseconds) to wait before a HTTP request times out. Set to 0 for unlimited.
		timeout = 30000
     ```
   * **READ FIRST:** You **will need** to set up `peripheral_config.txt`, and if necessary, `app.service.ts` as well based on your world's parameters. As noted in the introduction, the repository is in a nascent stage whereby developer engagement with source is a requirement.
   * Restart game.
   * Run `generic_peripheral_controller.lua` on the peripheral computers and record their IDs.
   * Execute `home` on the hub machine.

## Configuration

Tailor MineMate to your configuration:

* Edit `peripheral_config.txt` on the hub computer to associate devices/rooms with peripheral IDs (e.g., `lights_kitchen=2`)
* Modify `nestjs_server/src/app.service.ts` to expand `VALID_ROOMS` and `VALID_ACTIONS` for new devices or commands.
* Modify `home.lua` or `generic_peripheral_controller.lua` as necessary if modem/output sides or server URLs need adjusting.

The options are limitless, customize to suit your Minecraft world!