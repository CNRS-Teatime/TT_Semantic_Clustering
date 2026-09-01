import os

from ClusteringConcepts import *
from DistanceMatrix import *
from TermAssociation import *
import csv, logging, time
from dotenv import load_dotenv


def write_clusters_to_csv(gran_cluster_list: list[list[str]], path: str):
    """
    Writes all the clusterised objects, allong with their cluster ids, in a CSV file.
    The format for each row is:
    object_as_string, cluster_number

    :param gran_cluster_list: A 2D list of clusters, cluster_list[1] is the list of all ids in cluster 2
    :type gran_cluster_list: list[list[str]]
    :param path: The path to the desired csv file
    :type path: str
    """
    with open(path, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile, delimiter=',',quotechar='"')
        writer.writerow(['element', 'clusterNB'])
        for i in range(len(gran_cluster_list)):
            for element in gran_cluster_list[i]:
                writer.writerow([element, i])

if __name__ == "__main__":
    if not os.path.exists(".cache"):
        # if the .cache directory is not present
        # then create it.
        os.makedirs(".cache")

    logging.basicConfig(
        filename=".cache/clustering.log",
        encoding="utf-8",
        filemode="a",
        format="{asctime} - {levelname} - {message}",
        style="{",
        datefmt="%Y-%m-%d %H:%M",
        level=logging.INFO
    )

    load_dotenv()

    #Fetching and defining all constants
    CONCEPT_GRAPH_NAME = os.getenv("CONCEPTS_GRAPH")
    OBJECT_COLLECTION = os.getenv("NODE_COLLECTION")
    ASSOCIATION_GRAPH_NAME = os.getenv("ASSOCIATION_GRAPH")
    CONCEPT_MATRIX_PATH = f".cache/distance_matrix_{CONCEPT_GRAPH_NAME}.csv"
    OBJECT_MATRIX_PATH = f".cache/{OBJECT_COLLECTION}_distance_matrix_over_{CONCEPT_GRAPH_NAME}.csv"
    DATABASE = os.getenv("DB_NAME")
    HOST = os.getenv("DB_ADDRESS")
    USER = os.getenv("DB_USER")
    PASSWORD = os.getenv("DB_PASSWORD")
    NB_CLUSTERS = [int(n) for n in os.getenv("NB_CLUSTERS").split(',')]

    if not os.path.isdir(".cache"):
        os.makedirs(".cache")

    logging.log(logging.INFO, f"Starting clustering on objects from {OBJECT_COLLECTION} associated to {CONCEPT_GRAPH_NAME} via {ASSOCIATION_GRAPH_NAME}, in database {DATABASE}, with {NB_CLUSTERS} cluster")

    if os.path.isfile(CONCEPT_MATRIX_PATH):
        logging.log(logging.INFO, "Starting concept matrix fetching...")
        start = time.time()

        concept_ids, concept_matrix = fetch_distance_matrix(CONCEPT_MATRIX_PATH)

        logging.log(logging.INFO, f"Concept matrix fetched, took {time.time() - start}seconds")
    else :
        logging.log(logging.INFO, "Starting concept matrix calculations...")
        start = time.time()

        G = fetch_from_arango(CONCEPT_GRAPH_NAME, DATABASE)

        if G is None:
            logging.log(logging.ERROR,f"Graph '{CONCEPT_GRAPH_NAME}' is not in the database {DATABASE}")
            exit()

        concept_matrix = compute_concepts_matrix(G)
        concept_ids = list(G.nodes._nodes.keys())

        write_matrix_to_file(CONCEPT_MATRIX_PATH, concept_ids, concept_matrix)

        logging.log(logging.INFO, f"Concept matrix computed, took {time.time() - start}seconds")


    logging.log(logging.INFO, "Starting object concept mapping...")
    start = time.time()

    client = ArangoClient(hosts=HOST)
    db: database.StandardDatabase = client.db(DATABASE, username=USER, password=PASSWORD)

    object_maping = create_object_concept_map(db, OBJECT_COLLECTION, ASSOCIATION_GRAPH_NAME, concept_ids)

    logging.log(logging.INFO, f"Finished, took {time.time() - start}seconds")
    logging.log(logging.INFO, "Starting object distance matrix...")
    start = time.time()

    object_matrix = compute_object_matrix(concept_matrix, concept_ids, object_maping)
    object_ids = list(object_maping.keys())

    logging.log(logging.INFO, f"Finished, took {time.time() - start}seconds")

    write_matrix_to_file(OBJECT_MATRIX_PATH, object_ids, object_matrix)

    # These create a list, where clusters_X[i] returns the cluster number of item i in the original ids list
    id_to_cluster_mapping = compute_clusters(object_ids, object_matrix, NB_CLUSTERS, True)

    if os.getenv("PUSH_TO_DB") == "TRUE":
        add_cluster_back_to_db(id_to_cluster_mapping, DATABASE, USER, PASSWORD, HOST)
