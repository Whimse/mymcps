import os
import numpy as np
import json
from urllib.parse import urlparse  
#from langchain_core.prompts import ChatPromptTemplate
#from langchain_litellm import ChatLiteLLM

'''
def instance_from_json(cls, json_file:str):
    """
    Create an instance of the given class `cls`,
    using parameters loaded from `json_file`.
    """
    with open(json_file, "r") as f:
        params = json.load(f)

    if not isinstance(params, dict):
        raise ValueError("JSON file must contain an object (key-value pairs).")

    return cls(**params)


def load_model(json_file:str):
    
    with open(json_file, "r") as f:
        params = json.load(f)
        
    if not isinstance(params, dict):
        raise ValueError("JSON file must contain an object (key-value pairs).")

    if 'deepseek' in params['model']:
        os.environ["DEEPSEEK_API_KEY"] = params['api_key']
    
    model = ChatLiteLLM(**params)
    
    return model
'''

import re

def get_main_domain(url: str) -> str:
    netloc = urlparse(url).netloc or url
    parts = netloc.split('.')
    #if len(parts) >= 2:
    #    return parts[-2]
    return netloc

def extract_http_links(text: str) -> list[str]:
    """
    Return a list of all http / https links found in *text*.

    Notes
    -----
    • The regex is more strict about valid URL characters while still being practical
    • A second pass removes the most common trailing punctuation
      that authors often leave right after a link (e.g. a period).
    """
    # Main URL pattern (more strict about valid characters)
    url_pattern = r'''
        https?://                  # http or https
        (?:                         # start of non-capturing group
            [a-zA-Z0-9-]            # allowed characters in domain
            +(?:\.[a-zA-Z0-9-]+)*   # subdomains
            \.[a-zA-Z]{2,}          # top level domain (at least 2 chars)
            (?:/[a-zA-Z0-9-._~:/?#\[\]@!$&'()*+,;=%]*)?  # path and query
            |                        # OR
            localhost                # allow localhost
            |                        # OR
            \d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}  # IP addresses
        )
        (?<![/.,:;!?)}\]])          # negative lookbehind for common delimiters
    '''
    
    # Grab raw matches
    raw_links = re.findall(url_pattern, text, re.VERBOSE)
    
    # Clean off stray punctuation that might have been before lookbehind
    cleaned_links = [link.split("](")[0] for link in raw_links]
    
    return cleaned_links


'''
def query_document(model, document: str, question: str) -> str:
    """Ask a question about a document using a LangChain chat model."""
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a helpful assistant. Use the provided document to answer."),
        ("human", "Document:\n{document}\n\nQuestion: {question}")
    ])
    
    chain = prompt | model
    response = chain.invoke({"document": document, "question": question})
    
    return response.content if hasattr(response, "content") else str(response)


def update_document(model, document: str, instructions: str) -> str:
    """Modifies a text following some given instructions."""
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a helpful assistant. Update the provided document with the instructions."),
        ("human", "Document:\n{document}\nInstructions: {instructions}")
    ])
    
    chain = prompt | model
    response = chain.invoke({"document": document, "instructions": instructions})
    
    return response.content if hasattr(response, "content") else str(response)
'''
    
class UnionFind:
    """Union–Find with path‑compression and union‑by‑rank."""
    def __init__(self, n: int):
        self.parent = list(range(n))   # parent[i] = representative of i
        self.rank   = [0] * n          # upper bound on tree height
        self.sets   = n                # number of disjoint sets

    def find(self, x: int) -> int:
        """Return representative of the set containing x."""
        if self.parent[x] != x:                # not the root?
            self.parent[x] = self.find(self.parent[x])  # path compression
        return self.parent[x]

    def union(self, a: int, b: int) -> bool:
        """Merge sets containing a and b.  
        Returns True iff a merge actually happened."""
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return False                      # already in same set

        # union by rank (smaller tree hangs under larger)
        if self.rank[ra] < self.rank[rb]:
            ra, rb = rb, ra                   # ensure ra has ≥ rank
        self.parent[rb] = ra
        if self.rank[ra] == self.rank[rb]:
            self.rank[ra] += 1
        self.sets -= 1
        return True

    # optional helpers
    def connected(self, a: int, b: int) -> bool:
        return self.find(a) == self.find(b)

    def count(self) -> int:
        return self.sets
    
    # NEW --------------------------------------------------------
    def all_sets(self):
        """
        Return a list of components, each as a list of members.
        Example: [[0,1,5], [2,3,4]]
        """
        groups = {}
        for i in range(len(self.parent)):
            root = self.find(i)
            groups.setdefault(root, []).append(i)
            
        # sort members in each component for stable output
        sets = [sorted(members) for members in groups.values()]    
        
        sets = sorted(sets, key = lambda s:len(s), reverse=True)
        
        return sets
    

def embedding_distances(training, test, metric="cosine"):
    """
    Compute the distance between a test embedding and each training embedding.

    Parameters:
        training (array-like): A 2D array of shape (n_samples, n_features) containing training embeddings.
        test (array-like): A 1D array of shape (n_features,) representing a single test embedding.
        metric (str): Distance metric to use. Supported: "cosine", "euclidean". Default is "cosine".

    Returns:
        np.ndarray: A 1D array of distances between the test embedding and each training embedding.
    """
    
    training = np.asanyarray(training, dtype=float)
    test     = np.asanyarray(test,     dtype=float)

    if metric == "euclidean":
        # ‖x − y‖₂  for every row
        dists = np.linalg.norm(training - test, axis=1)

    elif metric == "cosine":
        # 1 − cos θ  (smaller ⇒ more similar)
        test_n      = test / np.linalg.norm(test)
        training_n  = training / np.linalg.norm(training, axis=1, keepdims=True)
        dists       = 1.0 - np.einsum("ij,j->i", training_n, test_n)

    else:
        raise ValueError("Unsupported metric")

    return dists


def nearest_descriptors(training, test, metric="cosine", k=2, threshold=1.0):
    """
    Find the nearest descriptors in the training set to a given test embedding.

    Parameters:
        training (array-like): A 2D array of training embeddings.
        test (array-like): A 1D array representing the test embedding.
        metric (str): Distance metric to use. Supported: "cosine", "euclidean". Default is "cosine".
        k (int or None): Maximum number of nearest neighbors to return. If None, return all under threshold.
        threshold (float): Maximum distance to consider a match. Default is 1.0.

    Returns:
        List[Tuple[int, float]]: A list of (index, distance) tuples sorted by increasing distance.
    """

    dists = embedding_distances(training, test, metric)
    
    # Distances with indexes
    result = list(enumerate(dists))
    
    # Sort distances by distance
    results = sorted(result, key=lambda e: e[1])

    # Purge distances longer than threshold
    results = [(idx, dist) for idx, dist in results if dist <= threshold]

    # Return top k
    if k:
        results = results[:k]
        
    return results


def nearest_matches(embs1, embs2, threshold: float = 0.3):
    """
    Find all nearest matches from embs1 to embs2 within a given distance threshold.

    Parameters:
        embs1 (array-like): A 2D array of embeddings to match from.
        embs2 (array-like): A 2D array of embeddings to match to.
        threshold (float): Maximum distance to consider a match. Default is 0.3.

    Returns:
        List[List[int, int, float]]: Sorted list of matches as [index_in_embs1, index_in_embs2, distance],
                                     ordered by increasing distance.
    """
    matches = []

    for idx1, emb1 in enumerate(embs1):
        for idx2, dist in nearest_descriptors(embs2, emb1, k=None, threshold=threshold):
            matches.append([idx1, idx2, dist])

    # Sanity check
    assert all(match[2] < threshold for match in matches)
    
    return sorted(matches, key=lambda r: r[2])


def find_central_idx(embeddings, metric="cosine"):
    """
    Finds the string whose embedding is closest to the centroid of the embedding cloud.

    Parameters:
        strings (List[str]): List of strings.
        embeddings (array-like): 2D array of shape (n_samples, n_features) with embeddings.
        metric (str): Distance metric to use. Supported: "cosine", "euclidean". Default is "cosine".

    Returns:
        str: The string closest to the centroid.
    """
    embeddings = np.asanyarray(embeddings, dtype=float)
    centroid = np.mean(embeddings, axis=0)

    distances = embedding_distances(embeddings, centroid, metric=metric)
    closest_idx = np.argmin(distances)

    return closest_idx

import random
import string

def random_string(length=10):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))


from bs4 import BeautifulSoup

def is_valid_html(s: str) -> bool:
    soup = BeautifulSoup(s, "html.parser")
    # If it finds at least one tag, and the original isn’t empty
    return bool(s.strip()) and bool(soup.find())


import os
import yaml
def load_credentials(path):
    
    if not path:
        return
    
    with open(path, "r") as f:
        credentials = yaml.safe_load(f)
        
        for key, value in credentials.items():
            if not isinstance(value, str):
                continue
            
            print(f"Adding environment variable {key}")
            os.environ[key] = value

        return credentials
    
