from unstructured.partition.auto import partition

def parse_document(file_path: str) -> str:
    elements = partition(filename=file_path)
    for element in elements[0:5]:
        print("Element : " + element.text)
        
    return "".join([el.text for el in elements if el.text])
