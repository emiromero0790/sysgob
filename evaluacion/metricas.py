import math


def precision_k(ranking, relevantes, k):
    return sum(1 for i in ranking[:k] if i in relevantes) / k


def recall_k(ranking, relevantes, k):
    return sum(1 for i in ranking[:k] if i in relevantes) / len(relevantes) if relevantes else 0.0


def precision_promedio(ranking, relevantes):
    aciertos, suma = 0, 0.0
    for posicion, identificador in enumerate(ranking, start=1):
        if identificador in relevantes:
            aciertos += 1
            suma += aciertos / posicion
    return suma / len(relevantes) if relevantes else 0.0


def ndcg_k(ranking, relevantes, k):
    dcg = sum(1 / math.log2(p + 1) for p, i in enumerate(ranking[:k], start=1) if i in relevantes)
    ideal = sum(1 / math.log2(p + 1) for p in range(1, min(k, len(relevantes)) + 1))
    return dcg / ideal if ideal else 0.0
