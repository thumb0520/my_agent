from dataclasses import dataclass


@dataclass
class WebResponse:

    def __init__(self, type: str, content: dict):
        self.type = type
        self.content = content

    def to_dict(self) -> dict:
        """
        Convert the WebResponse object to a dictionary for JSON serialization.
        
        Returns:
            dict: A dictionary representation of the WebResponse object
        """
        return {
            "type": self.type,
            "content": self.content
        }

    def __dict__(self) -> dict:
        """
        Make the class directly JSON serializable.
        
        Returns:
            dict: A dictionary representation of the WebResponse object
        """
        return self.to_dict()


if __name__ == "__main__":
    import json

    response = WebResponse("type", {"hello": "world"})
    print(json.dumps(response.to_dict(), ensure_ascii=False, indent=2))
