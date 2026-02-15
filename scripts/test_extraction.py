import ollama

llm_model = "gpt-oss:20b-cloud"

def test_extraction(query):
    prompt = f"""
    Extract the most important specific entities (people, places, products, concepts, identifiers like P1, P20) from the following query.
    Return ONLY a comma-separated list of names. No extra text.
    Query: {query}
    """
    response = ollama.generate(model=llm_model, prompt=prompt)
    print(f"Query: {query}")
    print(f"Response: {response['response']}")

if __name__ == "__main__":
    test_extraction("List the visits and prescriptions for patient P20.")
    test_extraction("What medications were prescribed for Raj Gomez?")
