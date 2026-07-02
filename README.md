# TEATIME Semantic Clustering

Semantic clustering experiment, part of the PRIME TEATIME PhD Thesis

***

## Description

This experiment performs semantic clustering based on a given thesaurus, which is stored inside an arangoDB instance. This clustering is performed on a arangoDB document collection which has been semanticaly linked to the thesaurus. Using Graph based distance in the thesaurus, a distance metric is calculated between documents in the collection allowing for agglomerative hierarchical clustering.

## Prerequisites

This utility does not generate or manage you ArangoDB instance. You need to refer to ArangoDB's [documentation](https://docs.arango.ai/arangodb/stable/get-started/). We recommend using the dockerised version of ArangoDB. Your arangoDB instance needs to be prepared via [TT_ArangoImporter](https://github.com/CNRS-Teatime/TT_ArangoImporter)

## Installation

We recommend using a virtual python environment through the [venv](https://docs.python.org/3/library/venv.html) python package. Simply replace `{foldername}` in the following command with the desired environment name (for ex Debug).
```bash
python3 -m venv {foldername}
```

Then activate the virtual environment :

### Unix/MacOS

```bash
source {foldername}/bin/activate
```

### Windows

```bash
./{foldername}/bin/activate
```

Finaly you can install the dependencies listed in requirements.txt via this command

```bash
python3 -m pip install -r requirements.txt
```

More info here : https://packaging.python.org/en/latest/guides/installing-using-pip-and-virtual-environments/

### Environment

A .env file needs to be created to define the arangoDB adress and credentials. As well as the clustering parameters.

| Variable          | Description                                                                                                         | Example        |
|-------------------|---------------------------------------------------------------------------------------------------------------------|----------------|
| NB_CLUSTERS       | Number of cluster for each granularities, the experiment is performed repeatedly for each chosen number of clusters | 16,32,64,128   |
| NODE_COLLECTION   | The node collection to clusterize                                                                                   | aioli_objects  |
| ASSOCIATION_GRAPH | The graph containing the semantic links between thesaurus and documents                                             | Semantic_graph |
| CONCEPTS_GRAPH    | The graph representing the desired thesaurus                                                                        | th15_graph     |
| PUSH_TO_DB        | Whether or not to push back the results directly to the Database                                                    | TRUE           |


An example can be found in the `.env-BOILERPLATE` file :
```dotenv
DB_ADDRESS="http://localhost:8529"
DB_NAME="DB_NAME"
DB_USER="USER"
DB_PASSWORD="TEST"


NB_CLUSTERS="64, 12, 256"
NODE_COLLECTION="aioli_objects"
ASSOCIATION_GRAPH="Semantic_graph"
CONCEPTS_GRAPH="th15_graph"
PUSH_TO_DB="TRUE"
```

## Usage

As long as the .env is set correctly you can simply run the script without any arguments

```bash
python3 src/clustering.py
```

## Results

Results are stored directly in the selected document collection, each document now contains a list named `clusters_with_CONCEPTS_GRAPH_NODE_COLLECTION` containing X cluster number, refering to the X different chosen granularities in the `NB_CLUSTERS` environment variable.

## License
This work is licenced under GNU GPL v3.0

## Project status
Finished
