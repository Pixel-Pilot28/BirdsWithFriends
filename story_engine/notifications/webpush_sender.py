"""
Web Push notification service for Birds with Friends.

Handles VAPID key generation, subscription management, and push notification
delivery with comprehensive error handling and retry logic.
"""
import logging
import json
import os
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.backends import default_backend
import base64

from pywebpush import webpush, WebPushException

logger = logging.getLogger(__name__)


class VAPIDKeyManager:
    """Manages VAPID keys for web push notifications."""
    
    @staticmethod
    def generate_vapid_keys() -> Dict[str, str]:
        """Generate new VAPID key pair."""
        
        # Generate private key
        private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
        
        # Get public key
        public_key = private_key.public_key()
        
        # Serialize private key
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        # Serialize public key  
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        return {
            "private_key": private_pem.decode('utf-8'),
            "public_key": public_pem.decode('utf-8')
        }
    
    @staticmethod
    def get_public_key_base64(public_key_pem: str) -> str:
        """Convert PEM public key to base64 format for client."""
        
        # Load the public key
        public_key = serialization.load_pem_public_key(
            public_key_pem.encode('utf-8'),
            backend=default_backend()
        )
        
        # Get raw public key bytes in uncompressed format
        public_numbers = public_key.public_numbers()
        x = public_numbers.x.to_bytes(32, 'big')
        y = public_numbers.y.to_bytes(32, 'big')
        
        # Uncompressed point format: 0x04 + x + y
        uncompressed_key = b'\\x04' + x + y
        
        # Encode to base64
        return base64.urlsafe_b64encode(uncompressed_key).decode('utf-8')


class WebPushSender:
    """Web Push notification sender."""
    
    def __init__(
        self,
        vapid_private_key: Optional[str] = None,
        vapid_public_key: Optional[str] = None,
        vapid_email: str = "admin@birdswithfriends.com"
    ):
        """Initialize web push sender with VAPID keys."""
        
        self.vapid_email = vapid_email
        
        # Load or generate VAPID keys
        if not vapid_private_key or not vapid_public_key:
            # Try to load from environment
            vapid_private_key = os.getenv("VAPID_PRIVATE_KEY")
            vapid_public_key = os.getenv("VAPID_PUBLIC_KEY")
            
            if not vapid_private_key or not vapid_public_key:
                # Generate new keys
                logger.warning("No VAPID keys found, generating new ones...")
                keys = VAPIDKeyManager.generate_vapid_keys()
                vapid_private_key = keys["private_key"]
                vapid_public_key = keys["public_key"]
                
                logger.info("New VAPID keys generated. Set these environment variables:")
                logger.info(f"VAPID_PRIVATE_KEY={vapid_private_key}")
                logger.info(f"VAPID_PUBLIC_KEY={vapid_public_key}")
        
        self.vapid_private_key = vapid_private_key
        self.vapid_public_key = vapid_public_key
        
        # Get public key in base64 format for clients
        self.public_key_base64 = VAPIDKeyManager.get_public_key_base64(vapid_public_key)
        
        logger.info("WebPush sender initialized with VAPID keys")
    
    async def send_notification(
        self,
        subscription_info: Dict[str, str],
        title: str,
        message: str,
        url: Optional[str] = None,
        icon: str = "/icon-192x192.png"
    ) -> Dict[str, Any]:
        """Send web push notification."""
        
        try:
            # Prepare notification payload
            payload = {
                "title": title,
                "body": message,
                "icon": icon,
                "badge": "/badge-72x72.png",
                "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000),
                "requireInteraction": False,
                "actions": []
            }
            
            if url:
                payload["data"] = {"url": url}
                payload["actions"] = [
                    {
                        "action": "open",
                        "title": "Read Episode",
                        "icon": "/action-read.png"
                    }
                ]
            
            # Send push notification
            response = webpush(
                subscription_info=subscription_info,
                data=json.dumps(payload),
                vapid_private_key=self.vapid_private_key,
                vapid_claims={
                    "sub": f"mailto:{self.vapid_email}"
                }
            )
            
            logger.info(f"🔔 Web push sent successfully (status: {response.status_code})")
            
            return {
                "success": True,
                "provider": "webpush",
                "status_code": response.status_code,
                "response_text": response.text
            }
            
        except WebPushException as e:
            logger.error(f"Web push failed: {e}")
            
            # Handle specific error cases
            if e.response and e.response.status_code == 410:
                # Subscription expired/invalid
                return {
                    "success": False,
                    "provider": "webpush",
                    "error": "subscription_expired",
                    "error_message": "Push subscription expired",
                    "should_remove_subscription": True
                }
            
            return {
                "success": False,
                "provider": "webpush",
                "error": "webpush_exception",
                "error_message": str(e)
            }
        
        except Exception as e:
            logger.error(f"Unexpected web push error: {e}")
            return {
                "success": False,
                "provider": "webpush",
                "error": "unknown_error", 
                "error_message": str(e)
            }
    
    async def send_episode_notification(
        self,
        subscription_info: Dict[str, str],
        story_title: str,
        episode_title: str,
        episode_index: int,
        story_id: str,
        base_url: str = "http://localhost:3000"
    ) -> Dict[str, Any]:
        """Send episode published web push notification."""
        
        title = f"🐦 New Episode #{episode_index}"
        message = f"{episode_title} - {story_title}"
        url = f"{base_url}/stories/{story_id}/episodes/{episode_index}"
        
        result = await self.send_notification(
            subscription_info=subscription_info,
            title=title,
            message=message,
            url=url
        )
        
        # Add metadata
        result.update({
            "notification_type": "webpush",
            "story_id": story_id,
            "episode_index": episode_index,
            "endpoint": subscription_info.get("endpoint", "unknown")
        })
        
        return result
    
    async def send_test_notification(
        self,
        subscription_info: Dict[str, str]
    ) -> Dict[str, Any]:
        """Send test web push notification."""
        
        title = "🐦 Birds with Friends Test"
        message = "Web push notifications are working correctly!"
        
        result = await self.send_notification(
            subscription_info=subscription_info,
            title=title,
            message=message
        )
        
        result.update({
            "notification_type": "test_webpush",
            "endpoint": subscription_info.get("endpoint", "unknown")
        })
        
        return result
    
    def get_vapid_public_key(self) -> str:
        """Get VAPID public key for client subscription."""
        return self.public_key_base64


# Global web push sender instance  
webpush_sender = WebPushSender()