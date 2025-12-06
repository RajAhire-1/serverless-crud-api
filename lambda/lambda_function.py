import json
import os
import boto3
from boto3.dynamodb.conditions import Key
from decimal import Decimal

dynamodb = boto3.resource("dynamodb")
TABLE_NAME = os.environ.get("TABLE_NAME", "serverless_items_jenkins")
table = dynamodb.Table(TABLE_NAME)


class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            if o % 1 == 0:
                return int(o)
            else:
                return float(o)
        return super().default(o)


def response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(body, cls=DecimalEncoder),
    }


def lambda_handler(event, context):
    http_method = event.get("httpMethod")
    path = event.get("path", "")
    path_params = event.get("pathParameters") or {}
    query_params = event.get("queryStringParameters") or {}

    print("Event received:", event)

    try:
        if http_method == "GET":
            # GET /items -> list all
            # GET /items/{id} -> get one
            if path.endswith("/items") and not path_params:
                return list_items()
            else:
                item_id = path_params.get("id")
                return get_item(item_id)

        elif http_method == "POST":
            # POST /items -> create
            body = json.loads(event.get("body") or "{}")
            return create_item(body)

        elif http_method == "PUT":
            # PUT /items/{id} -> update
            item_id = path_params.get("id")
            body = json.loads(event.get("body") or "{}")
            return update_item(item_id, body)

        elif http_method == "DELETE":
            # DELETE /items/{id}
            item_id = path_params.get("id")
            return delete_item(item_id)

        else:
            return response(405, {"message": "Method not allowed"})
    except Exception as e:
        print("Error:", str(e))
        return response(500, {"message": "Internal server error", "error": str(e)})


def list_items():
    result = table.scan()
    items = result.get("Items", [])
    return response(200, items)


def get_item(item_id):
    if not item_id:
        return response(400, {"message": "id is required in path"})
    result = table.get_item(Key={"id": item_id})
    item = result.get("Item")
    if not item:
        return response(404, {"message": "Item not found"})
    return response(200, item)


def create_item(body):
    if "id" not in body:
        return response(400, {"message": "Field 'id' is required"})
    table.put_item(Item=body)
    return response(201, body)


def update_item(item_id, body):
    if not item_id:
        return response(400, {"message": "id is required in path"})
    body["id"] = item_id
    table.put_item(Item=body)
    return response(200, body)


def delete_item(item_id):
    if not item_id:
        return response(400, {"message": "id is required in path"})
    table.delete_item(Key={"id": item_id})
    return response(204, {})


print("Auto deploy test from Jenkins")
