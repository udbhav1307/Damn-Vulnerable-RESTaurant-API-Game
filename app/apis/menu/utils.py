import base64
import ipaddress
import socket
from urllib.parse import urlparse

import requests
from apis.menu import schemas
from db.models import MenuItem, OrderItem
from fastapi import HTTPException


def _validate_image_url(image_url: str):
    parsed = urlparse(image_url)

    if parsed.scheme not in ("http", "https"):
        raise HTTPException(
            status_code=400, detail="image_url must use http or https"
        )

    if not parsed.hostname:
        raise HTTPException(
            status_code=400, detail="image_url must include a valid host"
        )

    try:
        resolved_ip = socket.gethostbyname(parsed.hostname)
    except socket.gaierror:
        raise HTTPException(
            status_code=400, detail="Could not resolve image_url host"
        )

    ip = ipaddress.ip_address(resolved_ip)
    if (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
    ):
        raise HTTPException(
            status_code=400,
            detail="image_url is not allowed to target internal/private addresses",
        )


def _image_url_to_base64(image_url: str):
    _validate_image_url(image_url)

    response = requests.get(
        image_url, stream=True, timeout=5, allow_redirects=False
    )

    content_type = response.headers.get("content-type", "")
    if not content_type.startswith("image/"):
        raise HTTPException(
            status_code=400, detail="image_url must point to an image"
        )

    encoded_image = base64.b64encode(response.content).decode()

    return encoded_image


def create_menu_item(
    db,
    menu_item: schemas.MenuItemCreate,
):
    menu_item_dict = menu_item.dict()
    image_url = menu_item_dict.pop("image_url", None)
    db_item = MenuItem(**menu_item_dict)

    if image_url:
        db_item.image_base64 = _image_url_to_base64(image_url)

    db.add(db_item)
    db.commit()
    db.refresh(db_item)

    return db_item


def update_menu_item(
    db,
    item_id: int,
    menu_item: schemas.MenuItemCreate,
):
    db_item = db.query(MenuItem).filter(MenuItem.id == item_id).first()
    if db_item is None:
        raise HTTPException(status_code=404, detail="Menu item not found")

    menu_item_dict = menu_item.dict()
    image_url = menu_item_dict.pop("image_url", None)

    for key, value in menu_item_dict.items():
        setattr(db_item, key, value)

    if image_url:
        db_item.image_base64 = _image_url_to_base64(image_url)

    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


def delete_menu_item(db, item_id: int):
    existing_order_item = (
        db.query(OrderItem).filter(OrderItem.menu_item_id == item_id).first()
    )
    if existing_order_item is not None:
        raise HTTPException(
            status_code=409,
            detail="You can not delete this menu item, it is associated with existing orders.",
        )

    db_item = db.query(MenuItem).filter(MenuItem.id == item_id).first()
    if db_item is None:
        raise HTTPException(status_code=404, detail="Menu item not found")

    db.delete(db_item)
    db.commit()
