"""
Hierarchical clustering on concepts using a precomputed distance matrix
"""
import numpy as np
import logging, os
from arango import ArangoClient, database
from sklearn.cluster import AgglomerativeClustering
from matplotlib import pyplot as plt
from scipy.cluster.hierarchy import dendrogram, fcluster
from sklearn.metrics import silhouette_score


def create_linkage_matrix(model) -> np.ndarray:
    # Create linkage matrix and then plot the dendrogram

    # create the counts of samples under each node
    counts = np.zeros(model.children_.shape[0])
    n_samples = len(model.labels_)
    for i, merge in enumerate(model.children_):
        current_count = 0
        for child_idx in merge:
            if child_idx < n_samples:
                current_count += 1  # leaf node
            else:
                current_count += counts[child_idx - n_samples]
        counts[i] = current_count

    linkage_matrix = np.column_stack(
        [model.children_, model.distances_, counts]
    ).astype(float)

    return linkage_matrix

def plot_dendrogram(model, **kwargs):
    plt.title("Hierarchical Clustering Dendrogram")
    # plot the top three levels of the dendrogram

    linkage_matrix = create_linkage_matrix(model)

    # Plot the corresponding dendrogram
    dendrogram(linkage_matrix, **kwargs)
    plt.xlabel("Number of points in node (or index of point if no parenthesis).")
    plt.show()

def fetch_distance_matrix(file_path : str) -> tuple[list ,np.ndarray]:
    """
    Fetch the distance matrix created by distanceMatrix.py
    :param file_path: the path to the distance matrix csv file
    :returns: The list of matrix, and a numpy 2D array representing the matrix as a tupple
    """
    with open(file_path, 'r') as f:
        ids = f.readline()
        ids = ids.split(',')
        for i in range(len(ids)):
            ids[i].replace('\n', '')
        size = len(ids)

        matrix : list = []

        for i in range(size):
            line = []
            for d in f.readline().split(','):
                if int(d) == -1:
                    line.append(10000000000000000000)
                else:
                    line.append(int(d))
            matrix.append(line[:size])


        return ids, np.asarray(matrix)


def compute_clusters(ids, matrix, nb_clusters: list[int], visualise_silouhette_score: bool = False) -> dict[str, list[int]]:
    """
    Based on a distance matrix csv file and a target number of cluster, computes
    the clusters. If the target number of clusters is higher than the number of objects, returns each object as its own
    cluster.

    :param matrix_csv: The path to the csv file containing a distance matrix
    :type matrix_csv: str
    :param nb_clusters: The target number of clusters
    :type nb_clusters: int
    :param visualise_silouhette_score: Wheter or not to visualise the silouhette score
    :type visualise_silouhette_score: bool

    :returns: A dictionary with object ids as keys and lists of cluster associated with the id as value
    """
    clustering = AgglomerativeClustering(metric="precomputed", linkage="average", distance_threshold=0, n_clusters=None)

    fitted_clustering = clustering.fit(matrix)

    linkage_matrix = create_linkage_matrix(fitted_clustering)

    granular_list: list[np.ndarray] = []

    nb_clusters.sort() # Just to make it easier to retrieve granularities

    score = []

    for n in nb_clusters: #Iterate over all desired granularity (max cluster number)

        result = fcluster(linkage_matrix, n, criterion='maxclust')

        #Silouhette score logging for further analysis
        sc = silhouette_score(matrix, result, metric="precomputed")
        logging.log(logging.INFO, f"Silouhette score for {n} cluster : {sc}")

        score.append(sc)

        granular_list.append(result)

    if visualise_silouhette_score :
        fig, ax = plt.subplots()

        ax.plot([str(x) for x in nb_clusters], score, label = "Silouhette score")
        ax.set_ylabel("Silouhette score")
        ax.set_xlabel("Number of clusters in the result")
        ax.set_title("Silouhette score at various granularity")

        plt.show()


    # These create a list, where clusters_X[i] returns the cluster number of item i in the original ids list
    id_to_cluster_mapping: dict = {}

    for i in range(len(granular_list)):
        for j in range(len(ids)):
            if not ids[j] in id_to_cluster_mapping:
                id_to_cluster_mapping[ids[j]] = []
            id_to_cluster_mapping[ids[j]].append(int(granular_list[i][j]))


    return id_to_cluster_mapping


def add_cluster_back_to_db(gran_clusters: dict[str, list[int]], db_name: str, db_user: str,
                           db_password: str, host_name: str = "http://localhost:8529") -> None:
    """
    Push back cluster numbers to arangoDB. The credentials are usually defined in a .env, fetched by the main function.
    :param gran_clusters: A dictionnary associating documents ids to a list of clusters it belongs to, with increasing granularity.
    :type gran_clusters: dict
    :param db_name: name of the associated database
    :type db_name: str
    :param db_user: usename to use for credentials
    :type db_user: str
    :param db_password: password associated with the username
    :type db_password: str
    :param host_name: The ArangoDB instance hostname (If local : http://localhost:8529 by default)
    :type host_name: str
    """
    client = ArangoClient(hosts=host_name)
    db: database.StandardDatabase = client.db(db_name, username=db_user, password=db_password)

    document_collections : dict[str, database.StandardCollection] = {}

    for id in gran_clusters.keys():
        collection_name = id.split('/')[0]
        if not db.has_collection(collection_name):
            continue
        if not collection_name in document_collections:
            document_collections[collection_name] = db.collection(collection_name)

        if document_collections[collection_name].has(id):
            document_collections[collection_name].update({'_id': id, f"clusters_with_{os.getenv("CONCEPTS_GRAPH")}_{os.getenv("NODE_COLLECTION")}": gran_clusters[id]}, silent=True)

if __name__ == "__main__":

    NB_CLUSTERS = [8, 16, 32, 64, 128, 256, 512, 1024]

    # These create a list, where clusters_X[i] returns the cluster number of item i in the original ids list
    cluster_mapping = compute_clusters("/Users/marwan/Code/TEATIME_PhD_Experiments/data/Clustering/clean_distance_matrix_th15_graph.csv", NB_CLUSTERS)

    # add_cluster_back_to_db( "th15", clusters, ids, "TEATIME", "root", "test")