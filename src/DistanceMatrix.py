from typing import Optional
from arango import ArangoClient, database
import networkx as nx
import logging
import numpy as np

def fetch_from_arango(graph_name : str, database_name : str, weights : dict = None) -> Optional[nx.DiGraph]:
    """
    From a list of edge collection, fetches the objects in those collection in the associated database.
    Those edges are inserted inside a networkx directed graph, which is returned by the function

    :param graph_name: The graph to fetch in the arangoDB instance
    :type graph_name: str
    :param database_name: The name of the database the funciton will use to fetch the collections
    :type database_name: str
    :returns: A networkx directed graph with arangodb document ids as node labels, or None if the graph does not exist.
    """

    client = ArangoClient(hosts="http://localhost:8529")
    db: database.StandardDatabase = client.db(database_name, username="root", password="test")

    if not db.has_graph(graph_name):
        return None

    if weights is None:
        weights = {
            'narrower': 1,
            'broader': 1,
            'related': 3,
            'closeMatch': 1.5,
            'exactMatch': 0
        }

    edge_collections : list = db.graph(graph_name).edge_collections()

    edges_as_list : list = []

    for coll in edge_collections:
        edge_coll: database.StandardCollection = db.collection(coll)
        edge_cursor = edge_coll.all()
        for edge in edge_cursor:
            if edge['type'] in weights:
                edges_as_list.append((edge['_from'], edge['_to'], int(weights[edge['type']])))
            else:
                edges_as_list.append((edge['_from'], edge['_to'], 1))


    Gr: nx.DiGraph = nx.DiGraph()
    Gr.add_weighted_edges_from(edges_as_list)

    return Gr


def compute_concepts_matrix(graph : nx.DiGraph) -> np.ndarray:
    """
    Computes a pairwise distance matrix for all the nodes in the given networkx Directed graph.

    :param graph: Any networkX directed graph with labeled nodes
    :type graph: networkx.DiGraph
    :return: A 2D matrix in the form of a list of list of ints
    """
    bf_path_length_dict : dict = dict(nx.all_pairs_bellman_ford_path_length(graph, weight='weight'))
    document_ids_as_list : list[str] = list(graph.nodes._nodes.keys())
    n = len(document_ids_as_list) # number of nodes

    fail = 0

    # Initializing an n by n zero matrix where n is the number of nodes in the graph
    distance_matrix  = np.array([[0 for i in range(n)] for j in range(n)])

    for i in range(n):
        for j in range(i + 1, n):
            if i != j:
                if document_ids_as_list[i] in bf_path_length_dict:
                    if document_ids_as_list[j] in bf_path_length_dict[document_ids_as_list[i]]: # The dictionary returned only has keys for reachable node pairs.
                        distance = bf_path_length_dict[document_ids_as_list[i]][document_ids_as_list[j]]
                    else: # The node pair is not reachable
                        distance = 10000000 # TODO : I need to find a better way
                        fail += 1
                else: # All nodes must have an outgoing entry in the matrix
                    raise ArithmeticError
            else: # Same node so no distance
                distance = 0

            distance_matrix[i][j] = distance_matrix[j][i] = distance

    logging.log(logging.WARNING, f"Fails {(fail/(n*n)) * 100}%")
    return distance_matrix

def distance_between_sets_of_concepts(set1 : list[str], set2 : list[str], concept_matrix: np.ndarray, concept_ids_map: dict[str, int]):
    dist = 0
    for c1 in set1:
        for c2 in set2:
            dist += concept_matrix[concept_ids_map[c1]][concept_ids_map[c2]]

    return dist / (len(set1) * len(set2))

def map_concept_id_to_index(c_ids: list) -> dict[str, int]:
    concept_id_map : dict[str, int] = {}

    for i in range(len(c_ids)):
        concept_id_map[c_ids[i]] = i

    return concept_id_map

def compute_object_matrix(concept_matrix: np.ndarray, concept_ids: list[str], object_mapping: dict[str, list[str]]) -> np.ndarray:
    """
    From a concept distance matrix and a map of object to concept set, build a distance matrix between all the objects.
    :param concept_matrix: A 2D Matrix representing the distance between concepts
    :param concept_ids: The list of concept ids present in the matrix, in the same ordrer as the matrix
    :param object_mapping: A mapping from object ids to sets of concept ids

    :returns: A 2D distance matrix between all sets of concepts
    """
    #Filtering out objects that have empty concept sets

    n = int(len(object_mapping))
    distance_matrix = np.array([[0 for i in range(n)] for j in range(n)])
    objects_ids = np.array(list(object_mapping.keys()))
    concept_ids_map : dict[str, int] = map_concept_id_to_index(concept_ids)


    for i in range(n):
        for j in range(i+1, n):
            if len(object_mapping[objects_ids[i]]) == 0 or len(object_mapping[objects_ids[j]]) == 0:
                distance = -1
            else:
                distance = distance_between_sets_of_concepts(object_mapping[objects_ids[i]], object_mapping[objects_ids[j]], concept_matrix, concept_ids_map)

            distance_matrix[i][j] = distance_matrix[j][i] = distance

    return distance_matrix


def write_matrix_to_file(file_name : str, document_id_list : list[str], mat: np.ndarray) -> None:
    """
    Write the distance matrix as a csv into a given file.
    The first row is the list of document ids.
    The others contain a row of commas separated ints, for each row in the matrix.
    The matrix can take a long time to compute, but we will reuse it a lot later on so this is useful

    :param file_name: The name of the file
    :type file_name: str
    :param document_id_list: A vector of document ids, in the same order they appear in the matrix
    :type document_id_list: list[str]
    :param mat: A 2D distance matrix
    :type mat: list[list[int]]
    """

    with open(file_name, 'w') as f:
        id_string: str = ""
        for i in range(len(document_id_list)):
            if i == len(document_id_list) - 1:
                id_string += str(document_id_list[i]) + '\n'
            else:
                id_string += str(document_id_list[i]) + ','
        f.write(id_string)

        for line in mat :
            line_string : str = ""
            for i in range(len(line)):
                if i == len(line) - 1:
                    line_string += str(line[i]) + '\n'
                else:
                    line_string += str(line[i]) + ','
            f.write(line_string)

if __name__ == "__main__":
    DATABASE = "TEATIME-Exp"
    GRAPH_NAME = "InterTheso_graph"

    G = fetch_from_arango(GRAPH_NAME, DATABASE)

    matrix = compute_concepts_matrix(G)

    print(f"{len(matrix)} x {len(matrix[0])} matrix produced")

    write_matrix_to_file(f"distance_matrix_{GRAPH_NAME}.csv", list(G.nodes._nodes.keys()), matrix)
