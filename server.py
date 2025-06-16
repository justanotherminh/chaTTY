from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import json
import uvicorn
from typing import List

# FastAPI app
app = FastAPI()

# Server-side message storage
messages: List[str] = []

# Keep track of connected clients
connected_clients: List[WebSocket] = []

# HTML client for testing
html_client = """
<!DOCTYPE html>
<html>
<head>
    <title>WebSocket Message Client</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; }
        #messages { border: 1px solid #ccc; height: 300px; overflow-y: auto; padding: 10px; margin: 20px 0; }
        .message { padding: 5px; border-bottom: 1px solid #eee; }
        input[type="text"] { width: 70%; padding: 10px; }
        button { padding: 10px 20px; }
        .status { color: green; font-weight: bold; }
        .error { color: red; font-weight: bold; }
    </style>
</head>
<body>
    <h1>WebSocket Message App</h1>
    <div id="status" class="status">Connecting...</div>
    
    <div>
        <input type="text" id="messageInput" placeholder="Enter your message..." />
        <button onclick="sendMessage()">Send Message</button>
    </div>
    
    <div id="messages"></div>

    <script>
        const ws = new WebSocket("/ws");
        const messagesDiv = document.getElementById('messages');
        const messageInput = document.getElementById('messageInput');
        const statusDiv = document.getElementById('status');

        ws.onopen = function(event) {
            statusDiv.textContent = "Connected to server";
            statusDiv.className = "status";
        };

        ws.onmessage = function(event) {
            const data = JSON.parse(event.data);
            
            if (data.type === 'all_messages') {
                // Clear and display all messages
                messagesDiv.innerHTML = '';
                data.messages.forEach(msg => addMessageToUI(msg));
            } else if (data.type === 'new_message') {
                // Add single new message
                addMessageToUI(data.message);
            }
        };

        ws.onclose = function(event) {
            statusDiv.textContent = "Disconnected from server";
            statusDiv.className = "error";
        };

        ws.onerror = function(error) {
            statusDiv.textContent = "Connection error";
            statusDiv.className = "error";
        };

        function addMessageToUI(message) {
            const messageDiv = document.createElement('div');
            messageDiv.className = 'message';
            messageDiv.textContent = message;
            messagesDiv.appendChild(messageDiv);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }

        function sendMessage() {
            const message = messageInput.value.trim();
            if (message) {
                ws.send(JSON.stringify({
                    type: 'send_message',
                    message: message
                }));
                messageInput.value = '';
            }
        }

        // Allow Enter key to send message
        messageInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                sendMessage();
            }
        });
    </script>
</body>
</html>
"""

@app.get("/")
async def get_client():
    """Serve the HTML client for testing"""
    return HTMLResponse(html_client)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.append(websocket)
    
    try:
        # Send all existing messages to the newly connected client
        await websocket.send_text(json.dumps({
            "type": "all_messages",
            "messages": messages
        }))
        
        print(f"Client connected. Total clients: {len(connected_clients)}")
        print(f"Sent {len(messages)} existing messages to new client")
        
        # Listen for messages from this client
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            if message_data["type"] == "send_message":
                new_message = message_data["message"]
                
                # Store message in server-side list
                messages.append(new_message)
                print(f"Stored message: '{new_message}'. Total messages: {len(messages)}")
                
                # Broadcast the new message to all connected clients
                disconnected_clients = []
                for client in connected_clients:
                    try:
                        await client.send_text(json.dumps({
                            "type": "new_message",
                            "message": new_message
                        }))
                    except:
                        # Client disconnected, mark for removal
                        disconnected_clients.append(client)
                
                # Remove disconnected clients
                for client in disconnected_clients:
                    connected_clients.remove(client)
                    
    except WebSocketDisconnect:
        connected_clients.remove(websocket)
        print(f"Client disconnected. Total clients: {len(connected_clients)}")

if __name__ == "__main__":
    print("Starting WebSocket server...")
    print("Server will store messages in memory and serve them to new clients")
    print("Current messages in storage:", messages)
    
    uvicorn.run(app, host="0.0.0.0", port=8000)