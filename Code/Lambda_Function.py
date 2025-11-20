import json
import os
import boto3

ddb = boto3.resource("dynamodb")
TABLE_NAME = os.environ.get("TABLE_NAME", "CommunityResources")

def _cors_headers():
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET,OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type,Authorization",
    }

def _to_jsonable(obj):
    """Recursively convert DynamoDB-deserialized types (e.g., set) into JSON-safe types."""
    if isinstance(obj, set):
        return sorted(list(obj))  # list is JSON-serializable; sort for stable output
    if isinstance(obj, dict):
        return {k: _to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_jsonable(v) for v in obj]
    return obj

def lambda_handler(event, context):
    params = event.get("queryStringParameters") or {}
    category = (params.get("category") or "").strip().lower()
    query = (params.get("query") or "").strip().lower()

    table = ddb.Table(TABLE_NAME)
    resp = table.scan()
    items = resp.get("Items", [])

    def matches(item):
        ok = True
        if category:
            ok = ok and item.get("category", "").lower() == category
        if query:
            # convert possible set to list of strings for searching
            tags = item.get("tags", [])
            if isinstance(tags, set):
                tags = list(tags)
            hay = " ".join([item.get("name", ""), " ".join(tags if isinstance(tags, list) else [])]).lower()
            ok = ok and (query in hay)
        return ok

    filtered = [ _to_jsonable(i) for i in items if matches(i) ]

    return {
        "statusCode": 200,
        "headers": _cors_headers(),
        "body": json.dumps({"count": len(filtered), "items": filtered})
    }
