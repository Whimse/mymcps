import os
import json
import urllib.request
import time
from typing import Optional, Dict, Any, List
import io
import uuid
import json
import urllib.request
import threading
from typing import Optional, Dict, Any

class TelegramHelper:
    """
    A class to interact with the Telegram Bot API using the standard library.
    """

    def __init__(self):
        """
        Initializes the bot instance.
        
        Raises:
            ValueError: If TELEGRAM_BOT_TOKEN or TELEGRAM_USER_ID are missing.
        """
        self.token = os.getenv('TELEGRAM_BOT_TOKEN')
        user_id_env = os.getenv('TELEGRAM_USER_ID')
        
        if not self.token:
            raise ValueError("Environment variable 'TELEGRAM_BOT_TOKEN' is not set.")
        if not user_id_env:
            raise ValueError("Environment variable 'TELEGRAM_USER_ID' is not set.")
            
        self.allowed_user_id = int(user_id_env)
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        self.offset = 0


    def get_user_name(self):
            """
            Retrieves user details from Telegram based on user_id.
            """
            url = f"{self.base_url}/getChat?chat_id={self.allowed_user_id}"
            
            try:
                with urllib.request.urlopen(url) as response:
                    data = json.loads(response.read().decode())
                    
                    if data.get("ok"):
                        chat = data["result"]
                        # Priority: Username -> First Name + Last Name -> First Name
                        username = chat.get("username")
                        first_name = chat.get("first_name", "")
                        last_name = chat.get("last_name", "")
                        
                        if username:
                            return f"@{username}"
                        return f"{first_name} {last_name}".strip()
                    
                    return "User not found"
            except Exception as e:
                return f"Error: {e}"
            
        
    def _execute_method(self, method_name: str, params: Optional[Dict] = None, blocking: bool = True) -> Optional[Dict[str, Any]]:
        """
        Executes a POST request to the API.

        Args:
            method_name (str): The API method to call.
            params (Optional[Dict]): Dictionary of parameters for the request.
            blocking (bool): If True, waits for response. If False, runs in background.

        Returns:
            Optional[Dict[str, Any]]: The JSON response if blocking=True, else None.
        """
        url = f"{self.base_url}/{method_name}"
        data = json.dumps(params).encode('utf-8') if params else None
        headers = {'Content-Type': 'application/json'}
        
        req = urllib.request.Request(url, data=data, headers=headers, method='POST')

        def perform_request():
            try:
                with urllib.request.urlopen(req) as response:
                    return json.loads(response.read().decode('utf-8'))
            except Exception as e:
                return {"ok": False, "error": str(e)}

        if blocking:
            # Standard behavior: Execute and return result
            return perform_request()
        else:
            # Non-blocking: Run in a separate thread and return None immediately
            thread = threading.Thread(target=perform_request, daemon=True)
            thread.start()
            return None

    def get_updates(self) -> List[Dict[str, Any]]:
        """
        Fetches new updates from Telegram.

        Returns:
            List[Dict[str, Any]]: A list of new update objects.
        """
        params = {"offset": self.offset, "timeout": 30}
        result = self._execute_method("getUpdates", params)
        updates = result.get("result", [])
        
        if updates:
            self.offset = updates[-1]["update_id"] + 1
        return updates


    def send_message(self, text: str) -> Dict[str, Any]:
        """
        Sends a message to a default recipient.

        Args:
            text (str): The content of the message, it can use HTML notation to format text

        Returns:
            Dict[str, Any]: The API response.
        """
        payload = {
            "chat_id": self.allowed_user_id,
            "text": text,
            "parse_mode": "HTML"
        }
        return self._execute_method("sendMessage", payload)


    def send_chat_action(self, action: str = "typing") -> Dict[str, Any]:
            """
            Tells the user that something is happening (e.g., 'typing', 'upload_photo').
            
            A quick, polite way to let the user know you are generating a response to a message.
            
            Args:
                action (str): The type of action to broadcast. 
                            Options: 'typing', 'upload_photo', 'record_video', 
                            'upload_document', 'find_location', etc.
            """
            payload = {
                "chat_id": self.allowed_user_id,
                "action": action
            }
            return self._execute_method("sendChatAction", payload, blocking = False)


    def send_image(self, pil_image, caption: Optional[str] = None) -> Dict[str, Any]:
        """
        Sends a PIL Image object to the allowed user.

        Args:
            pil_image: A PIL.Image object.
            caption (Optional[str]): Text to accompany the photo.

        Returns:
            Dict[str, Any]: The API response.
        """
        
        # 1. Convert PIL Image to bytes
        img_byte_arr = io.BytesIO()
        # You can change 'PNG' to 'JPEG' if preferred
        pil_image.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        file_bytes = img_byte_arr.read()

        # 2. Prepare Multipart Form Data
        boundary = f"Boundary-{uuid.uuid4()}"
        headers = {'Content-Type': f'multipart/form-data; boundary={boundary}'}
        
        # Build the body parts
        body = []
        
        # Add chat_id
        body.append(f'--{boundary}'.encode())
        body.append(f'Content-Disposition: form-data; name="chat_id"'.encode())
        body.append(b'')
        body.append(str(self.allowed_user_id).encode())
        
        # Add caption if exists
        if caption:
            body.append(f'--{boundary}'.encode())
            body.append(f'Content-Disposition: form-data; name="caption"'.encode())
            body.append(b'')
            body.append(caption.encode())

        # Add the photo file
        body.append(f'--{boundary}'.encode())
        body.append(f'Content-Disposition: form-data; name="photo"; filename="image.png"'.encode())
        body.append(b'Content-Type: image/png')
        body.append(b'')
        body.append(file_bytes)
        
        body.append(f'--{boundary}--'.encode())
        body.append(b'')

        payload = b'\r\n'.join(body)
        
        # 3. Execute request
        url = f"{self.base_url}/sendPhoto"
        req = urllib.request.Request(url, data=payload, headers=headers, method='POST')
        
        try:
            with urllib.request.urlopen(req) as response:
                return json.loads(response.read().decode('utf-8'))
        except Exception as e:
            return {"ok": False, "error": str(e)}

if __name__ == "__main__":
    try:
        bot = TelegramHelper()
        print(f"Bot listening for User ID: {bot.allowed_user_id}")

        while True:
            updates = bot.get_updates()
            for update in updates:
                if "message" in update:
                    user_id = update["message"]["from"]["id"]
                    chat_id = update["message"]["chat"]["id"]
                    text = update["message"].get("text", "")
                    if user_id == bot.allowed_user_id:
                        bot.send_message(f"<b>Echo</b>: {text}")
            
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nExit.")
        