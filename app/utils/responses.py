"""Helper bentuk response sukses: {"data": ..., "meta": ...}."""
from flask import jsonify, url_for


def success(data, status=200, meta=None):
    body = {"data": data}
    if meta is not None:
        body["meta"] = meta
    return jsonify(body), status


def created(data, endpoint, **url_values):
    """201 Created + header Location ke resource baru."""
    response, status = success(data, 201)
    response.headers["Location"] = url_for(endpoint, **url_values)
    return response, status


def no_content():
    return "", 204
