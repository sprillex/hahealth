from pydantic import BaseModel

class ShoppingListItem(BaseModel):
    name: str
