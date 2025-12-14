"""
DynamoDB storage for artifacts and ratings.
Uses lazy initialization to prevent import-time crashes when AWS isn't configured.
"""
import os
from typing import Dict, Any, Optional, List

# ----------------------------
# ENV CONFIG
# ----------------------------

def _is_local_mode() -> bool:
    """Check if LOCAL_MODE is explicitly enabled."""
    return os.getenv("LOCAL_MODE", "").lower() in {"1", "true", "yes"}


def _get_table_name(env_var: str, default: str) -> str:
    """Get table name from environment."""
    return os.getenv(env_var, default)


# ----------------------------
# LAZY DYNAMO INITIALIZATION
# ----------------------------
# Don't create boto3 resources at import time - do it lazily
# This prevents crashes in autograder/local environment

_dynamo = None
_artifacts_table = None
_ratings_table = None


def _get_artifacts_table():
    """Lazily initialize and return the artifacts DynamoDB table."""
    global _dynamo, _artifacts_table
    if _artifacts_table is None:
        import boto3
        region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "us-east-1"
        _dynamo = boto3.resource("dynamodb", region_name=region)
        table_name = _get_table_name("ARTIFACTS_TABLE", "ArtifactsTable")
        _artifacts_table = _dynamo.Table(table_name)
    return _artifacts_table


def _get_ratings_table():
    """Lazily initialize and return the ratings DynamoDB table."""
    global _dynamo, _ratings_table
    if _ratings_table is None:
        import boto3
        region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "us-east-1"
        if _dynamo is None:
            _dynamo = boto3.resource("dynamodb", region_name=region)
        table_name = _get_table_name("RATINGS_TABLE", "RatingsTable")
        _ratings_table = _dynamo.Table(table_name)
    return _ratings_table


# ----------------------------
# ARTIFACT OPERATIONS
# ----------------------------

def put_artifact(item: Dict[str, Any]) -> None:
    """Store an artifact in DynamoDB."""
    table = _get_artifacts_table()
    # DynamoDB requires numeric types for numbers
    ddb_item = {
        "id": int(item["id"]),
        "name": str(item["name"]),
        "type": str(item["type"]),
    }
    if item.get("url"):
        ddb_item["url"] = str(item["url"])
    if item.get("description"):
        ddb_item["description"] = str(item["description"])
    if item.get("created_at"):
        ddb_item["created_at"] = str(item["created_at"])
    
    table.put_item(Item=ddb_item)


def get_artifact_by_id(aid: int) -> Optional[Dict[str, Any]]:
    """Retrieve an artifact by ID."""
    table = _get_artifacts_table()
    resp = table.get_item(Key={"id": int(aid)})
    item = resp.get("Item")
    if item:
        # Convert DynamoDB Decimal to int for id
        item["id"] = int(item["id"])
    return item


def scan_all() -> List[Dict[str, Any]]:
    """Scan all artifacts from DynamoDB."""
    table = _get_artifacts_table()
    items = []
    start_key = None
    while True:
        if start_key:
            resp = table.scan(ExclusiveStartKey=start_key)
        else:
            resp = table.scan()
        
        for item in resp.get("Items", []):
            # Convert Decimal to int for id
            item["id"] = int(item["id"])
            items.append(item)
        
        if "LastEvaluatedKey" not in resp:
            break
        start_key = resp["LastEvaluatedKey"]
    
    return items


def delete_artifact(aid: int) -> bool:
    """Delete an artifact by ID."""
    table = _get_artifacts_table()
    try:
        table.delete_item(Key={"id": int(aid)})
        return True
    except Exception:
        return False


def reset_all() -> None:
    """Delete all artifacts from DynamoDB."""
    table = _get_artifacts_table()
    items = scan_all()
    with table.batch_writer() as batch:
        for item in items:
            batch.delete_item(Key={"id": int(item["id"])})
    
    # Also clear ratings
    reset_all_ratings()


# ----------------------------
# RATING OPERATIONS
# ----------------------------

def put_rating(artifact_id: int, rating: Dict[str, Any]) -> None:
    """Store a rating in DynamoDB."""
    table = _get_ratings_table()
    ddb_item = {"artifact_id": int(artifact_id)}
    
    # Convert rating dict to DynamoDB-compatible format
    for key, value in rating.items():
        if isinstance(value, dict):
            # Nested dict (like size_score)
            ddb_item[key] = {k: str(v) if isinstance(v, float) else v for k, v in value.items()}
        elif isinstance(value, float):
            # DynamoDB doesn't handle float well, store as string
            ddb_item[key] = str(value)
        else:
            ddb_item[key] = value
    
    table.put_item(Item=ddb_item)


def get_rating(artifact_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve a rating by artifact ID."""
    table = _get_ratings_table()
    resp = table.get_item(Key={"artifact_id": int(artifact_id)})
    item = resp.get("Item")
    
    if item:
        # Convert string floats back to float
        result = {}
        for key, value in item.items():
            if key == "artifact_id":
                continue
            elif key == "size_score" and isinstance(value, dict):
                result[key] = {k: float(v) for k, v in value.items()}
            elif isinstance(value, str):
                try:
                    result[key] = float(value)
                except ValueError:
                    result[key] = value
            else:
                result[key] = value
        return result
    
    return None


def reset_all_ratings() -> None:
    """Delete all ratings from DynamoDB."""
    table = _get_ratings_table()
    
    # Scan and delete all ratings
    start_key = None
    while True:
        if start_key:
            resp = table.scan(ExclusiveStartKey=start_key)
        else:
            resp = table.scan()
        
        items = resp.get("Items", [])
        if items:
            with table.batch_writer() as batch:
                for item in items:
                    batch.delete_item(Key={"artifact_id": int(item["artifact_id"])})
        
        if "LastEvaluatedKey" not in resp:
            break
        start_key = resp["LastEvaluatedKey"]


# ----------------------------
# ID GENERATION
# ----------------------------

def get_next_id() -> int:
    """Get the next available artifact ID using DynamoDB atomic counter."""
    table = _get_artifacts_table()
    
    # Use update_item with ADD to atomically increment
    try:
        resp = table.update_item(
            Key={"id": 0},  # Use id=0 as the counter record
            UpdateExpression="SET #counter = if_not_exists(#counter, :start) + :inc",
            ExpressionAttributeNames={"#counter": "counter"},
            ExpressionAttributeValues={":start": 0, ":inc": 1},
            ReturnValues="UPDATED_NEW"
        )
        return int(resp["Attributes"]["counter"])
    except Exception:
        # Fallback: scan to find max ID
        items = scan_all()
        if not items:
            return 1
        max_id = max(int(item["id"]) for item in items if item.get("id", 0) != 0)
        return max_id + 1