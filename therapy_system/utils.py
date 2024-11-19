from typing import Generator, Union

def escape_special_characters(text : Union[str, Generator[str, None, None]]) -> Union[str, Generator[str, None, None]]:
    rules = lambda x: x.replace("$", "\$").replace("*", "\*")
    if isinstance(text, Generator):
        for chunk in text:
            yield rules(chunk)
    else:
        return rules(text)

def unescape_special_characters(text : str) -> str:
    rules = lambda x: x.replace("\$", "$").replace("\*", "*")
    return rules(text)
    #     for chunk in text:
    #         yield rules(chunk)
    # else:
    #     return rules(text)
