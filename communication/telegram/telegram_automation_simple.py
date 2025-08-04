#!/usr/bin/env python3
"""
Telegram Automation Tool - Simple JSON Convention (Fixed Version)
Simplified version using Convention over Configuration approach with proper aiotdlib handling
"""

# --- Ensure working directory is the script's directory (for Python process usage only) ---
import os, sys
if hasattr(sys, 'argv') and sys.argv[0]:
    script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    if script_dir and os.path.isdir(script_dir):
        try:
            os.chdir(script_dir)
            # Debug output removed to prevent JSON contamination
        except Exception:
            # Silently handle any directory change errors
            pass
# --- End working directory fix ---

import json
import sys
import os
import asyncio
import signal
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path
from contextlib import contextmanager
from io import StringIO
import datetime

# Suppress aiotdlib and related library logging to prevent output contamination
logging.getLogger('aiotdlib').setLevel(logging.CRITICAL)
logging.getLogger('telegram').setLevel(logging.CRITICAL)
logging.getLogger('tdlib').setLevel(logging.CRITICAL)
logging.getLogger('asyncio').setLevel(logging.WARNING)
# Disable all logging for clean JSON output
logging.basicConfig(level=logging.CRITICAL)

@contextmanager
def suppress_stderr():
    """Context manager to suppress stderr output from C++ libraries using file descriptor redirection"""
    # Save the original stderr file descriptor
    original_stderr_fd = os.dup(2)
    try:
        # Open /dev/null (or NUL on Windows) to redirect stderr
        devnull = os.open(os.devnull, os.O_WRONLY)
        # Redirect stderr file descriptor to /dev/null
        os.dup2(devnull, 2)
        os.close(devnull)
        yield
    finally:
        # Restore the original stderr file descriptor
        os.dup2(original_stderr_fd, 2)
        os.close(original_stderr_fd)

# Test mode for autodiscovery
if len(sys.argv) > 1 and sys.argv[1] == '{"__test__": true}':
    print('{"success": true, "_simple": true}')
    sys.exit(0)

# Schema dump for fractalic introspection
if len(sys.argv) > 1 and sys.argv[1] in ["--fractalic-dump-schema", "--fractalic-dump-multi-schema"]:
    schema = {
        "name": "telegram_automation_simple",
        "description": "Telegram automation tool using TDLib for reading chats, sending messages, getting user profiles, and more. Uses simple JSON input/output contract.",
        "command": "simple-json",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "get_chats",
                        "get_messages", 
                        "send_message",
                        "get_user_profile",
                        "search_chats",
                        "get_chat_members"
                    ],
                    "description": "Telegram function to execute."
                },
                "chat_id": {
                    "type": "integer",
                    "description": "Telegram chat ID (for get_messages, send_message, get_chat_members)"
                },
                "chat_identifier": {
                    "oneOf": [
                        {"type": "integer"},
                        {"type": "string"}
                    ],
                    "description": "Chat ID (integer) or chat title (string) to identify the chat (for get_messages, send_message, get_chat_members)"
                },
                "user_id": {
                    "type": "integer", 
                    "description": "Telegram user ID (for get_user_profile)"
                },
                "text": {
                    "type": "string",
                    "description": "Message text to send (for send_message)"
                },
                "query": {
                    "type": "string",
                    "description": "Search query for chats (for search_chats)"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results to return (default varies by function)"
                },
                "chat_type": {
                    "type": "string",
                    "enum": [
                        "all",
                        "private", 
                        "group",
                        "channel"
                    ],
                    "description": "Filter chats by type (for get_chats)"
                },
                "parse_mode": {
                    "type": "string",
                    "enum": [
                        "text",
                        "markdown"
                    ],
                    "description": "Text parsing mode (for send_message)"
                },
                "from_message_id": {
                    "type": "integer",
                    "description": "Start from specific message ID, 0 for latest (for get_messages)"
                },
                "include_author_details": {
                    "type": "boolean",
                    "description": "Whether to fetch detailed author information (requires additional API calls, default: true)"
                }
            },
            "required": [
                "action"
            ]
        }
    }
    print(json.dumps(schema, indent=2, ensure_ascii=False))
    sys.exit(0)

@dataclass
class TelegramConfig:
    """Configuration for Telegram client using aiotdlib"""
    api_id: int
    api_hash: str
    phone: str
    database_encryption_key: str = "myencryptionkey123"
    use_test_dc: bool = False
    device_model: str = "Fractalic Telegram Tool"
    system_version: str = "1.0"
    application_version: str = "1.0"
    system_language_code: str = "en"
    files_directory: str = "tdlib_files"

def get_credentials_config_path() -> Path:
    """Get path to credentials configuration file"""
    # First try local directory (next to the script)
    local_path = Path(__file__).parent / "telegram_credentials.json"
    if local_path.exists():
        return local_path
    
    # Fallback to home directory
    return Path.home() / ".fractalic" / "telegram_credentials.json"

def load_credentials() -> Optional[Dict[str, Any]]:
    """Load credentials from configuration file"""
    try:
        config_path = get_credentials_config_path()
        if not config_path.exists():
            return None
        
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Failed to load credentials: {e}", file=sys.stderr)
        return None

async def resolve_chat_id(client, chat_identifier) -> Optional[int]:
    """Resolve chat identifier (ID or title) to chat ID"""
    if isinstance(chat_identifier, int):
        return chat_identifier
    
    if isinstance(chat_identifier, str):
        # First try to parse as integer
        try:
            return int(chat_identifier)
        except ValueError:
            pass
        
        # Search for chat by title
        try:
            # Get all chats and find by title
            await client.api.load_chats(limit=1000)
            chat_list_result = await client.api.get_chats(
                chat_list={'@type': 'chatListMain'},
                limit=1000
            )
            
            for chat_id in chat_list_result.chat_ids:
                try:
                    chat = await client.api.get_chat(chat_id=chat_id)
                    if hasattr(chat, 'title') and chat.title == chat_identifier:
                        return chat.id
                except Exception:
                    continue
            
            # If not found in main list, try searching
            search_result = await client.api.search_chats(
                query=chat_identifier,
                limit=50
            )
            
            for chat_id in search_result.chat_ids:
                try:
                    chat = await client.api.get_chat(chat_id=chat_id)
                    if hasattr(chat, 'title') and chat.title == chat_identifier:
                        return chat.id
                except Exception:
                    continue
                    
        except Exception:
            pass
    
    return None

async def execute_get_chats(client, limit: int = 100, chat_type: str = "all") -> Dict[str, Any]:
    """Get list of chats"""
    try:
        chats = []
        await client.api.load_chats(limit=limit)
        
        chat_list_result = await client.api.get_chats(
            chat_list={'@type': 'chatListMain'},
            limit=limit
        )
        
        for chat_id in chat_list_result.chat_ids[:limit]:
            try:
                chat = await client.api.get_chat(chat_id=chat_id)
                
                chat_info = {
                    "id": chat.id,
                    "title": getattr(chat, 'title', 'Unknown'),
                    "type": chat.type_.__class__.__name__ if hasattr(chat, 'type_') else 'unknown',
                    "unread_count": getattr(chat, 'unread_count', 0)
                }
                
                chats.append(chat_info)
                
            except Exception:
                continue  # Skip chats that can't be processed
        
        me = await client.api.get_me()
        return {
            "success": True,
            "chats": chats,
            "total_count": len(chats),
            "user_info": {
                "id": me.id,
                "phone": me.phone_number
            }
        }
        
    except Exception as e:
        return {"error": f"Failed to get chats: {str(e)}"}

async def execute_get_messages(client, chat_id: int, limit: int = 50, from_message_id: int = 0, include_author_details: bool = True) -> Dict[str, Any]:
    """Get messages from a chat with comprehensive information (with advanced TDLib pagination)"""
    try:
        messages = []
        author_cache = {}
        fetched = 0
        next_from_message_id = from_message_id
        consecutive_empty_calls = 0
        max_consecutive_empty_calls = 5  # Allow more empty calls before giving up
        total_api_calls = 0
        max_api_calls = min(limit * 2, 500)  # Prevent infinite loops but allow many attempts
        small_batch_attempts = 0
        
        # Step 1: Try to open the chat first to ensure it's properly loaded
        # This is especially important for channels/groups
        try:
            await client.api.open_chat(chat_id=chat_id)
            await asyncio.sleep(0.2)  # Give TDLib time to load chat info
        except Exception:
            # Ignore errors - chat might already be open or this might not be needed
            pass
        
        # Step 2: TDLib pagination with persistent strategy
        # Research shows TDLib often returns only 1 message per call initially,
        # but will gradually return more as its cache builds up
        while fetched < limit and total_api_calls < max_api_calls:
            total_api_calls += 1
            
            # Progressive batch sizing: start small, gradually increase
            if total_api_calls <= 5:
                batch_size = min(20, limit - fetched)  # Start with smaller requests
            elif total_api_calls <= 15:
                batch_size = min(50, limit - fetched)  # Medium size
            else:
                batch_size = min(100, limit - fetched)  # Full size
            
            # Get chat history
            chat_history = await client.api.get_chat_history(
                chat_id=chat_id,
                limit=batch_size,
                from_message_id=next_from_message_id,
                offset=0,
                only_local=False  # Always force server fetch
            )
            
            if not chat_history.messages:
                consecutive_empty_calls += 1
                # TDLib might need more time to load history from server
                if consecutive_empty_calls < max_consecutive_empty_calls:
                    await asyncio.sleep(0.3)  # Longer wait for server loading
                    continue
                else:
                    break
            else:
                consecutive_empty_calls = 0  # Reset counter on any fetch
                
                # If we got very few messages (like 1) on early attempts,
                # this is TDLib's normal behavior - continue requesting more
                if len(chat_history.messages) == 1 and small_batch_attempts < 20:
                    small_batch_attempts += 1
                    # Brief pause to let TDLib load more into cache
                    await asyncio.sleep(0.15)
            
            for message in chat_history.messages:
                try:
                    content = getattr(message, 'content', None)
                    text = ""
                    content_type = "unknown"
                    attachments = []
                    if content:
                        content_type = content.__class__.__name__ if hasattr(content, '__class__') else 'unknown'
                        if hasattr(content, 'text') and content.text:
                            raw_text = content.text.text if hasattr(content.text, 'text') else str(content.text)
                            try:
                                text = raw_text.encode('utf-8', errors='replace').decode('utf-8')
                            except (UnicodeDecodeError, UnicodeEncodeError):
                                text = str(raw_text)
                        if content_type == "messagePhoto":
                            attachments.append({
                                "type": "photo",
                                "caption": getattr(content, 'caption', {}).get('text', '') if hasattr(content, 'caption') else ''
                            })
                            if hasattr(content, 'caption') and content.caption:
                                text = content.caption.text if hasattr(content.caption, 'text') else str(content.caption)
                        elif content_type == "messageDocument":
                            doc_info = {
                                "type": "document",
                                "file_name": getattr(content.document, 'file_name', 'unknown') if hasattr(content, 'document') else 'unknown',
                                "mime_type": getattr(content.document, 'mime_type', 'unknown') if hasattr(content, 'document') else 'unknown'
                            }
                            attachments.append(doc_info)
                            if hasattr(content, 'caption') and content.caption:
                                text = content.caption.text if hasattr(content.caption, 'text') else str(content.caption)
                        elif content_type == "messageVideo":
                            attachments.append({
                                "type": "video",
                                "duration": getattr(content.video, 'duration', 0) if hasattr(content, 'video') else 0
                            })
                            if hasattr(content, 'caption') and content.caption:
                                text = content.caption.text if hasattr(content.caption, 'text') else str(content.caption)
                        elif content_type == "messageAudio":
                            attachments.append({
                                "type": "audio",
                                "duration": getattr(content.audio, 'duration', 0) if hasattr(content, 'audio') else 0
                            })
                        elif content_type == "messageSticker":
                            attachments.append({
                                "type": "sticker",
                                "emoji": getattr(content.sticker, 'emoji', '') if hasattr(content, 'sticker') else ''
                            })
                        elif content_type == "messageVoiceNote":
                            attachments.append({
                                "type": "voice_note",
                                "duration": getattr(content.voice_note, 'duration', 0) if hasattr(content, 'voice_note') else 0
                            })
                        elif content_type == "messageVideoNote":
                            attachments.append({
                                "type": "video_note",
                                "duration": getattr(content.video_note, 'duration', 0) if hasattr(content, 'video_note') else 0
                            })
                    sender_id = None
                    sender_info = None
                    if hasattr(message, 'sender_id'):
                        if hasattr(message.sender_id, 'user_id'):
                            sender_id = message.sender_id.user_id
                        elif hasattr(message.sender_id, 'chat_id'):
                            sender_id = message.sender_id.chat_id
                    if include_author_details and sender_id and sender_id not in author_cache:
                        try:
                            if sender_id > 0:
                                user = await client.api.get_user(user_id=sender_id)
                                author_cache[sender_id] = {
                                    "user_id": user.id,
                                    "first_name": getattr(user, 'first_name', ''),
                                    "last_name": getattr(user, 'last_name', ''),
                                    "username": getattr(user, 'username', ''),
                                    "is_bot": getattr(user, 'type', {}).get('@type') == 'userTypeBot' if hasattr(user, 'type') else False
                                }
                            else:
                                chat = await client.api.get_chat(chat_id=sender_id)
                                author_cache[sender_id] = {
                                    "chat_id": chat.id,
                                    "title": getattr(chat, 'title', 'Unknown'),
                                    "type": chat.type_.__class__.__name__ if hasattr(chat, 'type_') else 'unknown'
                                }
                        except Exception:
                            author_cache[sender_id] = {"id": sender_id, "error": "Could not fetch details"}
                    if include_author_details and sender_id:
                        sender_info = author_cache.get(sender_id)
                    reply_to_message_id = None
                    if hasattr(message, 'reply_to_message_id') and message.reply_to_message_id:
                        reply_to_message_id = message.reply_to_message_id
                    forward_info = None
                    if hasattr(message, 'forward_info') and message.forward_info:
                        forward_info = {
                            "date": getattr(message.forward_info, 'date', 0),
                            "from_chat_id": getattr(message.forward_info.origin, 'chat_id', None) if hasattr(message.forward_info, 'origin') else None,
                            "from_message_id": getattr(message.forward_info.origin, 'message_id', None) if hasattr(message.forward_info, 'origin') else None
                        }
                    dt = datetime.datetime.fromtimestamp(message.date, tz=datetime.timezone.utc)
                    iso_date = dt.isoformat()
                    message_info = {
                        "id": message.id,
                        "date": iso_date,
                        "chat_id": message.chat_id,
                        "sender_id": sender_id,
                        "is_outgoing": message.is_outgoing,
                        "text": text,
                        "content_type": content_type,
                        "attachments": attachments,
                        "reply_to_message_id": reply_to_message_id,
                        "forward_info": forward_info
                    }
                    if sender_info:
                        message_info["author"] = sender_info
                    messages.append(message_info)
                except Exception:
                    continue
            fetched += len(chat_history.messages)
            
            # For next batch: use the oldest message ID we received
            # TDLib's get_chat_history excludes the from_message_id, so we can use it directly
            if chat_history.messages:
                next_from_message_id = chat_history.messages[-1].id
            
            # Stop if we got fewer messages than requested AND we've made enough attempts
            # TDLib research shows we need to persist even with small returns
            if len(chat_history.messages) < batch_size and total_api_calls > 50:
                break
            
            # Special case: if we consistently get 1 message and have made many attempts,
            # this might be all that's available in the local cache
            if len(chat_history.messages) == 1 and total_api_calls > 100:
                break
        
        # TDLib returns messages in reverse chronological order (newest first)
        # For user convenience, return messages in chronological order (oldest first)
        messages.sort(key=lambda m: m["date"])
        
        # Ensure we don't return more than the requested limit
        if len(messages) > limit:
            messages = messages[:limit]
        return {
            "success": True,
            "messages": messages,
            "total_count": len(messages),
            "chat_id": chat_id,
            "debug_info": {
                "requested_limit": limit,
                "total_api_calls": total_api_calls,
                "total_fetched": fetched,
                "final_message_count": len(messages),
                "pagination_message_id": next_from_message_id,
                "empty_calls_encountered": consecutive_empty_calls,
                "small_batch_attempts": small_batch_attempts
            }
        }
    except Exception as e:
        return {"error": f"Failed to get messages: {str(e)}"}

async def execute_send_message(client, chat_id: int, text: str, parse_mode: str = "text") -> Dict[str, Any]:
    """Send a message to a chat"""
    try:
        from aiotdlib.api import FormattedText
        
        message_content = {
            "@type": "inputMessageText",
            "text": FormattedText(text=text, entities=[])
        }
        
        # Send the message
        result = await client.api.send_message(
            chat_id=chat_id,
            input_message_content=message_content
        )
        
        return {
            "success": True,
            "message_id": result.id,
            "chat_id": chat_id,
            "text": text,
            "date": result.date
        }
        
    except Exception as e:
        return {"error": f"Failed to send message: {str(e)}"}

async def execute_get_chat_members(client, chat_id: int, limit: int = 200) -> Dict[str, Any]:
    """Get members of a chat"""
    try:
        # Get basic chat info first
        chat = await client.api.get_chat(chat_id=chat_id)
        
        # Get chat members using searchChatMembers
        members_result = await client.api.search_chat_members(
            chat_id=chat_id,
            query="",  # Empty query to get all members
            limit=limit
        )
        
        members = []
        for member in members_result.members:
            try:
                # Get user info for each member
                user = await client.api.get_user(user_id=member.member_id.user_id)
                
                member_info = {
                    "user_id": member.member_id.user_id,
                    "status": member.status.__class__.__name__ if hasattr(member, 'status') else 'unknown',
                    "first_name": getattr(user, 'first_name', ''),
                    "last_name": getattr(user, 'last_name', ''),
                    "username": getattr(user, 'username', ''),
                    "is_bot": getattr(user, 'type', {}).get('@type') == 'userTypeBot' if hasattr(user, 'type') else False
                }
                
                members.append(member_info)
                
            except Exception:
                continue  # Skip members that can't be processed
        
        return {
            "success": True,
            "chat_id": chat_id,
            "chat_title": getattr(chat, 'title', 'Unknown'),
            "members": members,
            "total_count": len(members)
        }
        
    except Exception as e:
        return {"error": f"Failed to get chat members: {str(e)}"}

async def execute_get_user_profile(client, user_id: int) -> Dict[str, Any]:
    """Get user profile information"""
    try:
        user = await client.api.get_user(user_id=user_id)
        
        # Get full user info
        user_full_info = await client.api.get_user_full_info(user_id=user_id)
        
        # Extract bio text safely
        bio = ""
        if hasattr(user_full_info, 'bio') and user_full_info.bio:
            if hasattr(user_full_info.bio, 'text'):
                bio = user_full_info.bio.text
            else:
                bio = str(user_full_info.bio)
        
        user_info = {
            "user_id": user.id,
            "first_name": getattr(user, 'first_name', ''),
            "last_name": getattr(user, 'last_name', ''),
            "username": getattr(user, 'username', ''),
            "phone_number": getattr(user, 'phone_number', ''),
            "is_bot": getattr(user, 'type', {}).get('@type') == 'userTypeBot' if hasattr(user, 'type') else False,
            "is_verified": getattr(user, 'is_verified', False),
            "is_premium": getattr(user, 'is_premium', False),
            "bio": bio,
            "has_private_chats": getattr(user_full_info, 'has_private_chats', True)
        }
        
        return {
            "success": True,
            "user": user_info
        }
        
    except Exception as e:
        return {"error": f"Failed to get user profile: {str(e)}"}

async def execute_search_chats(client, query: str, limit: int = 20) -> Dict[str, Any]:
    """Search for chats by name or username"""
    try:
        # Search for chats
        search_result = await client.api.search_chats(
            query=query,
            limit=limit
        )
        
        chats = []
        for chat_id in search_result.chat_ids:
            try:
                chat = await client.api.get_chat(chat_id=chat_id)
                
                chat_info = {
                    "id": chat.id,
                    "title": getattr(chat, 'title', 'Unknown'),
                    "type": chat.type_.__class__.__name__ if hasattr(chat, 'type_') else 'unknown',
                    "unread_count": getattr(chat, 'unread_count', 0)
                }
                
                chats.append(chat_info)
                
            except Exception:
                continue  # Skip chats that can't be processed
        
        return {
            "success": True,
            "query": query,
            "chats": chats,
            "total_count": len(chats)
        }
        
    except Exception as e:
        return {"error": f"Failed to search chats: {str(e)}"}

async def execute_telegram_function(action: str, **kwargs) -> Dict[str, Any]:
    """Execute a Telegram function with given parameters"""
    
    # Load credentials
    credentials = load_credentials()
    if not credentials:
        return {"error": "No credentials found. Please run initialization first."}
    
    # Create config
    config = TelegramConfig(
        api_id=credentials['api_id'],
        api_hash=credentials['api_hash'],
        phone=credentials['phone'],
        database_encryption_key=credentials.get('database_encryption_key', 'myencryptionkey123')
    )
    
    try:
        from aiotdlib import Client, ClientSettings
        
        settings = ClientSettings(
            api_id=config.api_id,
            api_hash=config.api_hash,
            phone_number=config.phone,
            database_encryption_key=config.database_encryption_key,
            use_test_dc=config.use_test_dc,
            device_model=config.device_model,
            system_version=config.system_version,
            application_version=config.application_version,
            system_language_code=config.system_language_code,
            files_directory=config.files_directory
        )
        
        # Simple client usage with robust cleanup handling
        # Temporarily disable stderr suppression for debugging
        # with suppress_stderr():
        client = None
        try:
            client = Client(settings=settings)
            await client.start()
            
            # Resolve chat_identifier to chat_id if needed
            chat_id = None
            if 'chat_identifier' in kwargs:
                chat_id = await resolve_chat_id(client, kwargs['chat_identifier'])
                if chat_id is None:
                    return {"error": f"Could not resolve chat identifier: {kwargs['chat_identifier']}"}
            elif 'chat_id' in kwargs:
                chat_id = kwargs['chat_id']
            
            # Execute the requested function based on action
            if action == "get_chats":
                result = await execute_get_chats(
                    client, 
                    limit=kwargs.get('limit', 100),
                    chat_type=kwargs.get('chat_type', 'all')
                )
            elif action == "get_messages":
                result = await execute_get_messages(
                    client,
                    chat_id=chat_id,
                    limit=kwargs.get('limit', 50),
                    from_message_id=kwargs.get('from_message_id', 0),
                    include_author_details=kwargs.get('include_author_details', True)
                )
            elif action == "send_message":
                result = await execute_send_message(
                    client,
                    chat_id=chat_id,
                    text=kwargs.get('text'),
                    parse_mode=kwargs.get('parse_mode', 'text')
                )
            elif action == "get_chat_members":
                result = await execute_get_chat_members(
                    client,
                    chat_id=chat_id,
                    limit=kwargs.get('limit', 200)
                )
            elif action == "get_user_profile":
                result = await execute_get_user_profile(
                    client,
                    user_id=kwargs.get('user_id')
                )
            elif action == "search_chats":
                result = await execute_search_chats(
                    client,
                    query=kwargs.get('query'),
                    limit=kwargs.get('limit', 20)
                )
            else:
                result = {"error": f"Unknown action: {action}. Available: get_chats, get_messages, send_message, get_chat_members, get_user_profile, search_chats"}
            
            return result
            
        finally:
            # Graceful cleanup with cancellation handling
            if client is not None:
                try:
                    await client.stop()
                except (asyncio.CancelledError, RuntimeError):
                    # Ignore cancellation errors during cleanup
                    pass
        
    except Exception as e:
        error_msg = str(e)
        if "PHONE_NUMBER_INVALID" in error_msg:
            return {"error": f"Invalid phone number format. Use format: +1234567890"}
        elif "API_ID_INVALID" in error_msg:
            return {"error": "Invalid API ID. Get your credentials from https://my.telegram.org"}
        elif "AUTH_KEY_UNREGISTERED" in error_msg:
            return {"error": "Authentication key is not registered. Try with real API credentials."}
        else:
            return {"error": f"Execution failed: {error_msg}"}

def main():
    """Main entry point for simple JSON contract"""
    # Handle different argument scenarios
    if len(sys.argv) == 1:
        # No arguments - provide default action or help
        print(json.dumps({
            "error": "No action specified",
            "available_actions": ["get_chats", "get_messages", "send_message"],
            "usage": "python3 telegram_automation_simple.py '{\"action\": \"get_chats\", \"limit\": 5}'"
        }, ensure_ascii=False))
        sys.exit(1)
    elif len(sys.argv) != 2:
        print(json.dumps({"error": "Usage: python3 telegram_automation_simple.py '{\"action\": \"get_chats\", ...}'"}, ensure_ascii=False))
        sys.exit(1)
    
    try:
        # Parse JSON input
        input_data = json.loads(sys.argv[1])
        
        # Extract action and parameters
        action = input_data.get('action')
        if not action:
            print(json.dumps({"error": "Missing 'action' field in input JSON"}, ensure_ascii=False))
            sys.exit(1)
        
        # Remove action from kwargs
        kwargs = {k: v for k, v in input_data.items() if k != 'action'}
        
        # Execute the function with asyncio.run (simple approach)
        result = asyncio.run(execute_telegram_function(action, **kwargs))
        
        # Output result as JSON
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"Invalid JSON input: {str(e)}"}, ensure_ascii=False))
        sys.exit(1)
    except KeyboardInterrupt:
        print(json.dumps({"error": "Operation cancelled by user"}, ensure_ascii=False))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"error": f"Execution failed: {str(e)}"}, ensure_ascii=False))
        sys.exit(1)

if __name__ == "__main__":
    main()
