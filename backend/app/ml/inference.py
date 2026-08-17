
from typing import Dict, List, Tuple, Set
from collections import defaultdict
import random
import math
from dataclasses import dataclass


@dataclass
class Order:
    order_id: str
    categories: List[str]


@dataclass
class AssociationRule:
    antecedent: Set[str]
    consequent: Set[str]
    support: float
    confidence: float
    lift: float


def run_inference(orders: List[Dict], min_support: float = 0.3, min_confidence: float = 0.7) -> Dict:
    
    parsed_orders = [Order(order_id=o['order_id'], categories=o['categories']) for o in orders]
    
    transactions = [set(order.categories) for order in parsed_orders]
    
    frequent_itemsets = fp_growth(transactions, min_support)
    rules = generate_association_rules(frequent_itemsets, transactions, min_confidence)
    affinity_matrix = build_affinity_matrix(rules)
    all_categories = list(set(cat for t in transactions for cat in t))
    slotting_map = generate_slotting_map(all_categories, affinity_matrix)
    
    batches = genetic_algorithm_batching(parsed_orders, affinity_matrix)
    
    total_distance_optimized = 0
    for batch in batches:
        route = optimize_picking_route(batch['order_ids'], slotting_map, parsed_orders)
        batch['picking_route'] = {
            "sequence": route['route'],
            "distance": route['total_distance'],
            "heuristic": "nearest-neighbor"
        }
        total_distance_optimized += route['total_distance']
    
    baseline_distances = calculate_baseline_distances(parsed_orders, slotting_map)
    distance_comparison = {
        "baseline_random": baseline_distances['random'],
        "baseline_abc": baseline_distances['abc'],
        "optimized": total_distance_optimized,
        "improvement_vs_random": round((baseline_distances['random'] - total_distance_optimized) / baseline_distances['random'] * 100, 2),
        "improvement_vs_abc": round((baseline_distances['abc'] - total_distance_optimized) / baseline_distances['abc'] * 100, 2)
    }
    
    metadata = {
        "total_orders": len(orders),
        "total_categories": len(all_categories),
        "total_batches": len(batches),
        "total_distance": round(total_distance_optimized, 2),
        "min_support_used": min_support,
        "min_confidence_used": min_confidence,
        "frequent_itemsets_count": len(frequent_itemsets),
        "rules_count": len(rules)
    }
    
    return {
        "slotting_map": slotting_map,
        "batches": batches,
        "distance_comparison": distance_comparison,
        "metadata": metadata
    }


def fp_growth(transactions: List[Set[str]], min_support: float) -> List[Set[str]]:
    
    item_counts = defaultdict(int)
    for transaction in transactions:
        for item in transaction:
            item_counts[item] += 1
    
    total_transactions = len(transactions)
    min_count = min_support * total_transactions
    
    frequent_items = {item for item, count in item_counts.items() if count >= min_count}
    
    frequent_itemsets = []
    for item in frequent_items:
        frequent_itemsets.append({item})
    
    for size in range(2, 5):
        new_itemsets = []
        for i, set1 in enumerate(frequent_itemsets):
            if len(set1) != size - 1:
                continue
            for set2 in frequent_itemsets[i+1:]:
                if len(set2) != size - 1:
                    continue
                union = set1 | set2
                if len(union) == size:
                    count = sum(1 for t in transactions if union.issubset(t))
                    if count >= min_count:
                        new_itemsets.append(union)
        frequent_itemsets.extend(new_itemsets)
        if not new_itemsets:
            break
    
    return frequent_itemsets


def generate_association_rules(
    frequent_itemsets: List[Set[str]], 
    transactions: List[Set[str]],
    min_confidence: float
) -> List[AssociationRule]:
    
    rules = []
    total_transactions = len(transactions)
    
    for itemset in frequent_itemsets:
        if len(itemset) < 2:
            continue
        
        for item in itemset:
            antecedent = itemset - {item}
            consequent = {item}
            
            antecedent_count = sum(1 for t in transactions if antecedent.issubset(t))
            if antecedent_count == 0:
                continue
            
            itemset_count = sum(1 for t in transactions if itemset.issubset(t))
            consequent_count = sum(1 for t in transactions if consequent.issubset(t))
            
            support = itemset_count / total_transactions
            confidence = itemset_count / antecedent_count
            lift = confidence / (consequent_count / total_transactions) if consequent_count > 0 else 0
            
            if confidence >= min_confidence:
                rules.append(AssociationRule(
                    antecedent=antecedent,
                    consequent=consequent,
                    support=support,
                    confidence=confidence,
                    lift=lift
                ))
    
    return rules


def build_affinity_matrix(rules: List[AssociationRule]) -> Dict[Tuple[str, str], float]:
    
    affinity = defaultdict(float)
    
    for rule in rules:
        for a in rule.antecedent:
            for c in rule.consequent:
                pair = tuple(sorted([a, c]))
                score = rule.support * rule.confidence * rule.lift
                affinity[pair] = max(affinity[pair], score)
    
    return dict(affinity)


def generate_slotting_map(categories: List[str], affinity_matrix: Dict[Tuple[str, str], float]) -> Dict[str, Dict[str, int]]:
    
    slotting_map = {}
    
    sorted_pairs = sorted(affinity_matrix.items(), key=lambda x: x[1], reverse=True)
    
    placed_categories = set()
    current_aisle = 0
    current_position = 0
    max_position = 4
    
    for (cat1, cat2), _ in sorted_pairs:
        if cat1 not in placed_categories:
            slotting_map[cat1] = {"aisle": current_aisle, "position": current_position}
            placed_categories.add(cat1)
            current_position += 1
        
        if cat2 not in placed_categories:
            if current_position > max_position:
                current_aisle += 1
                current_position = 0
            
            slotting_map[cat2] = {"aisle": current_aisle, "position": current_position}
            placed_categories.add(cat2)
            current_position += 1
            
            if current_position > max_position:
                current_aisle += 1
                current_position = 0
    
    for category in categories:
        if category not in placed_categories:
            if current_position > max_position:
                current_aisle += 1
                current_position = 0
            
            slotting_map[category] = {"aisle": current_aisle, "position": current_position}
            placed_categories.add(category)
            current_position += 1
            
            if current_position > max_position:
                current_aisle += 1
                current_position = 0
    
    return slotting_map


def genetic_algorithm_batching(orders: List[Order], affinity_matrix: Dict[Tuple[str, str], float], population_size: int = 50, generations: int = 100) -> List[Dict]:
    
    if len(orders) <= 3:
        return [{
            "batch_id": 0,
            "order_ids": [o.order_id for o in orders],
            "total_orders": len(orders)
        }]
    
    def calculate_fitness(individual: List[int]) -> float:
        batches = defaultdict(list)
        for idx, batch_id in enumerate(individual):
            batches[batch_id].append(orders[idx])
        
        total_affinity = 0
        for batch_orders in batches.values():
            for i, order1 in enumerate(batch_orders):
                for order2 in batch_orders[i+1:]:
                    for cat1 in order1.categories:
                        for cat2 in order2.categories:
                            pair = tuple(sorted([cat1, cat2]))
                            total_affinity += affinity_matrix.get(pair, 0)
        
        penalty = sum(1 for b in batches.values() if len(b) > 5) * 10
        return total_affinity - penalty
    
    def crossover(parent1: List[int], parent2: List[int]) -> Tuple[List[int], List[int]]:
        point = random.randint(1, len(parent1) - 1)
        child1 = parent1[:point] + parent2[point:]
        child2 = parent2[:point] + parent1[point:]
        return child1, child2
    
    def mutate(individual: List[int], max_batch: int) -> List[int]:
        if random.random() < 0.1:
            idx = random.randint(0, len(individual) - 1)
            individual[idx] = random.randint(0, max_batch)
        return individual
    
    max_batches = max(2, len(orders) // 5)
    
    population = [[random.randint(0, max_batches - 1) for _ in orders] for _ in range(population_size)]
    
    best_individual = None
    best_fitness = float('-inf')
    
    for generation in range(generations):
        fitness_scores = [calculate_fitness(ind) for ind in population]
        
        max_fitness = max(fitness_scores)
        if max_fitness > best_fitness:
            best_fitness = max_fitness
            best_individual = population[fitness_scores.index(max_fitness)]
        
        new_population = []
        
        elite_count = max(2, population_size // 10)
        elite_indices = sorted(range(population_size), key=lambda i: fitness_scores[i], reverse=True)[:elite_count]
        new_population.extend([population[i] for i in elite_indices])
        
        while len(new_population) < population_size:
            tournament_size = 3
            parent1_idx = max(random.sample(range(population_size), tournament_size), key=lambda i: fitness_scores[i])
            parent2_idx = max(random.sample(range(population_size), tournament_size), key=lambda i: fitness_scores[i])
            
            if random.random() < 0.8:
                child1, child2 = crossover(population[parent1_idx], population[parent2_idx])
            else:
                child1, child2 = population[parent1_idx][:], population[parent2_idx][:]
            
            child1 = mutate(child1, max_batches - 1)
            child2 = mutate(child2, max_batches - 1)
            
            new_population.extend([child1, child2])
        
        population = new_population[:population_size]
    
    batches_dict = defaultdict(list)
    for idx, batch_id in enumerate(best_individual):
        batches_dict[batch_id].append(orders[idx].order_id)
    
    batches = []
    for batch_id, order_ids in batches_dict.items():
        if order_ids:
            batches.append({
                "batch_id": batch_id,
                "order_ids": order_ids,
                "total_orders": len(order_ids)
            })
    
    return batches


def optimize_picking_route(order_ids: List[str], slotting_map: Dict[str, Dict[str, int]], orders: List[Order]) -> Dict:
    
    order_dict = {o.order_id: o for o in orders}
    
    locations = []
    for order_id in order_ids:
        if order_id in order_dict:
            order = order_dict[order_id]
            for category in order.categories:
                if category in slotting_map:
                    locations.append(slotting_map[category])
    
    if not locations:
        return {
            "order_ids": order_ids,
            "route": [],
            "total_distance": 0
        }
    
    unique_locations = [dict(t) for t in {tuple(d.items()) for d in locations}]
    
    if len(unique_locations) == 1:
        return {
            "order_ids": order_ids,
            "route": unique_locations,
            "total_distance": 0
        }
    
    route = [unique_locations[0]]
    remaining = unique_locations[1:]
    total_distance = 0
    
    while remaining:
        current = route[-1]
        nearest = min(remaining, key=lambda loc: manhattan_distance(current, loc))
        distance = manhattan_distance(current, nearest)
        total_distance += distance
        route.append(nearest)
        remaining.remove(nearest)
    
    return {
        "order_ids": order_ids,
        "route": route,
        "total_distance": round(total_distance, 2)
    }


def manhattan_distance(loc1: Dict[str, int], loc2: Dict[str, int]) -> float:
    
    return abs(loc1['aisle'] - loc2['aisle']) * 10 + abs(loc1['position'] - loc2['position'])


def calculate_baseline_distances(orders: List[Order], slotting_map: Dict[str, Dict[str, int]]) -> Dict[str, float]:
    
    total_distance_random = 0
    total_distance_abc = 0
    
    for order in orders:
        locations = [slotting_map[cat] for cat in order.categories if cat in slotting_map]
        if len(locations) < 2:
            continue
        
        random_locations = locations[:]
        random.seed(42)
        random.shuffle(random_locations)
        random_dist = sum(manhattan_distance(random_locations[i], random_locations[i+1]) for i in range(len(random_locations) - 1))
        total_distance_random += random_dist
        
        sorted_locations = sorted(locations, key=lambda loc: (loc['aisle'], loc['position']))
        abc_dist = sum(manhattan_distance(sorted_locations[i], sorted_locations[i+1]) for i in range(len(sorted_locations) - 1))
        total_distance_abc += abc_dist
    
    return {
        "random": round(total_distance_random, 2),
        "abc": round(total_distance_abc, 2)
    }