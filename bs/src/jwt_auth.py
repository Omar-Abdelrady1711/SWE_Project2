# bs/src/auth.py
"""
JWT-based authentication for the artifact registry using DynamoDB for user storage.
"""
import os
import time
import jwt
import bcrypt
import boto3
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import HTTPException, Header
from botocore.exceptions import ClientError

# JWT Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

# DynamoDB Configuration
LOCAL_MODE = os.getenv("LOCAL_MODE") == "true"
AWS_REGION = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "us-east-1"
USERS_TABLE = os.getenv("USERS_TABLE", "UsersTable")

# Pre-computed password hashes for initial users
ADMIN_PASSWORD_HASH = b'$2b$12$SEzE5hlA2RnXTPzUKEc2wuVLwoNyB8ABejWCtFbaNpQeWKXPyPFlW'  # admin123
USER_PASSWORD_HASH = b'$2b$12$T0qxhAKks2Ak0sjRMy1zhOuampHijddAdEuJkPn4K8uZrjS9.2qFq'   # user123

# DynamoDB Setup
if LOCAL_MODE:
    print("⚠️ LOCAL_MODE enabled → using in-memory user storage")
    # In-memory fallback for local development
    _USERS_MEMDB: Dict[str, Dict[str, Any]] = {
        "admin": {
            "username": "admin",
            "hashed_password": ADMIN_PASSWORD_HASH.decode('utf-8'),
            "role": "admin",
            "email": "admin@example.com",
        },
        "user": {
            "username": "user",
            "hashed_password": USER_PASSWORD_HASH.decode('utf-8'),
            "role": "user",
            "email": "user@example.com",
        },
    }
else:
    print(f"🔐 Using DynamoDB table '{USERS_TABLE}' for user storage")
    dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
    users_table = dynamodb.Table(USERS_TABLE)
    _USERS_MEMDB = None
    
    # Initialize default users in DynamoDB if they don't exist
    def _initialize_default_users():
        try:
            # Check if admin exists
            resp = users_table.get_item(Key={"username": "admin"})
            if "Item" not in resp:
                users_table.put_item(Item={
                    "username": "admin",
                    "hashed_password": ADMIN_PASSWORD_HASH.decode('utf-8'),
                    "role": "admin",
                    "email": "admin@example.com",
                })
                print("✅ Created default admin user")
            
            # Check if user exists
            resp = users_table.get_item(Key={"username": "user"})
            if "Item" not in resp:
                users_table.put_item(Item={
                    "username": "user",
                    "hashed_password": USER_PASSWORD_HASH.decode('utf-8'),
                    "role": "user",
                    "email": "user@example.com",
                })
                print("✅ Created default user")
        except ClientError as e:
            print(f"⚠️ Could not initialize default users: {e}")
    
    _initialize_default_users()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password using bcrypt directly."""
    password_bytes = plain_password.encode('utf-8')
    # Handle both bytes and string hashes (DynamoDB stores as string)
    if isinstance(hashed_password, str):
        hashed_password = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt directly. Returns string for DynamoDB storage."""
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')  # Store as string in DynamoDB


# DynamoDB User Operations
def _get_user_from_db(username: str) -> Optional[Dict[str, Any]]:
    """Get user from DynamoDB or in-memory store."""
    if LOCAL_MODE:
        return _USERS_MEMDB.get(username)
    
    try:
        resp = users_table.get_item(Key={"username": username})
        return resp.get("Item")
    except ClientError as e:
        print(f"Error getting user {username}: {e}")
        return None


def _put_user_to_db(user: Dict[str, Any]) -> None:
    """Put user to DynamoDB or in-memory store."""
    if LOCAL_MODE:
        _USERS_MEMDB[user["username"]] = user
    else:
        try:
            users_table.put_item(Item=user)
        except ClientError as e:
            print(f"Error putting user: {e}")
            raise HTTPException(status_code=500, detail="Failed to save user")


def _delete_user_from_db(username: str) -> None:
    """Delete user from DynamoDB or in-memory store."""
    if LOCAL_MODE:
        if username in _USERS_MEMDB:
            del _USERS_MEMDB[username]
    else:
        try:
            users_table.delete_item(Key={"username": username})
        except ClientError as e:
            print(f"Error deleting user: {e}")
            raise HTTPException(status_code=500, detail="Failed to delete user")


def _scan_all_users() -> list[Dict[str, Any]]:
    """Scan all users from DynamoDB or in-memory store."""
    if LOCAL_MODE:
        return list(_USERS_MEMDB.values())
    
    try:
        items = []
        response = users_table.scan()
        items.extend(response.get("Items", []))
        
        # Handle pagination
        while "LastEvaluatedKey" in response:
            response = users_table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
            items.extend(response.get("Items", []))
        
        return items
    except ClientError as e:
        print(f"Error scanning users: {e}")
        return []



def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and verify a JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


def authenticate_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    """Authenticate a user by username and password."""
    user = _get_user_from_db(username)
    if not user:
        return None
    if not verify_password(password, user["hashed_password"]):
        return None
    return user


def get_current_user(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    """
    Get the current authenticated user from the Authorization header.
    Expected format: "Bearer <token>"
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid authentication scheme")
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    
    payload = decode_access_token(token)
    username = payload.get("sub")
    if username is None:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    
    user = _get_user_from_db(username)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    
    return {
        "username": user["username"],
        "role": user["role"],
        "email": user["email"],
    }


def require_admin(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    """Require that the current user is an admin."""
    user = get_current_user(authorization)
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


def create_user(username: str, password: str, email: str, role: str = "user") -> Dict[str, Any]:
    """Create a new user (admin only operation)."""
    existing_user = _get_user_from_db(username)
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    if role not in ["user", "admin"]:
        raise HTTPException(status_code=400, detail="Invalid role")
    
    user = {
        "username": username,
        "hashed_password": get_password_hash(password),
        "role": role,
        "email": email,
    }
    _put_user_to_db(user)
    
    return {
        "username": user["username"],
        "role": user["role"],
        "email": user["email"],
    }


def get_all_users() -> list[Dict[str, Any]]:
    """Get all users (admin only operation)."""
    users = _scan_all_users()
    return [
        {
            "username": user["username"],
            "role": user["role"],
            "email": user["email"],
        }
        for user in users
    ]


def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    """Get a specific user by username (admin only operation)."""
    user = _get_user_from_db(username)
    if not user:
        return None
    
    return {
        "username": user["username"],
        "role": user["role"],
        "email": user["email"],
    }


def update_user(username: str, email: Optional[str] = None, role: Optional[str] = None, password: Optional[str] = None) -> Dict[str, Any]:
    """Update user information (admin only operation)."""
    user = _get_user_from_db(username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if email is not None:
        user["email"] = email
    
    if role is not None:
        if role not in ["user", "admin"]:
            raise HTTPException(status_code=400, detail="Invalid role")
        user["role"] = role
    
    if password is not None:
        user["hashed_password"] = get_password_hash(password)
    
    _put_user_to_db(user)
    
    return {
        "username": user["username"],
        "role": user["role"],
        "email": user["email"],
    }


def delete_user(username: str) -> bool:
    """Delete a user (admin only operation)."""
    user = _get_user_from_db(username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if username == "admin":
        raise HTTPException(status_code=400, detail="Cannot delete admin user")
    
    _delete_user_from_db(username)
    return True
