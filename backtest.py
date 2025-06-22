from kafka import KafkaConsumer
import json
import math
import numpy as np
from tqdm import trange
from datetime import datetime
import itertools

KAFKA_BROKER = 'localhost:9092'
KAFKA_TOPIC = 'mock_l1_stream'
CONSUMER_GROUP_ID = 'my_consumer_group'

FEES = 0.01
REBATE = 0.005

def allocate(order_size: int, venues: list[dict], lambda_over: float, lambda_under: float, theta_queue:float)-> tuple[list[int], float]:
    """
    Allocates a target order_size across multiple trading venues to minimize total expected cost.

    Args:
        order_size (int): Target shares to buy.
        venues (list): List of venue objects, each with 'ask', 'ask_size', 'fee', 'rebate'.
        lambda_over (float): Cost penalty per extra share bought.
        lambda_under (float): Cost penalty per unfilled share.
        theta_queue (float): Queue-risk penalty (linear in total mis-execution).

    Returns:
        tuple: (best_split, best_cost)
            best_split (list[int]): Shares sent to each venue (len == N).
            best_cost (float): Total expected cost of that split.
    """
    step = 100  # search in 100-share chunks
    splits = [[]]  # start with an empty allocation list

    # Generate all possible discrete allocations
    for v_idx in range(len(venues)):
        new_splits = []
        for alloc in splits:
            used = sum(alloc)
            # Max shares to allocate to current venue: cannot exceed remaining order_size
            # and cannot exceed available ask_size at this venue.
            max_v = min(order_size - used, venues[v_idx]['ask_sz_00'])

            # Iterate through possible quantities (q) to send to the current venue
            # in steps of 'step'. Ensure q does not exceed max_v.
            # Handle the case where max_v is not a multiple of step by including max_v.
            for q in range(0, max_v + step, step):
                if q > max_v:  # Avoid exceeding max_v for the last step
                    q = max_v
                new_splits.append(alloc + [q])
                if q == max_v: # If we've reached max_v, no need to add more steps
                    break
        splits = new_splits

    best_cost = math.inf
    best_split = []

    # Evaluate each generated split
    for alloc in splits:
        # Only consider allocations where the total shares allocated exactly match the order_size
        if sum(alloc) != order_size:
            continue

        cost = compute_cost(alloc, venues, order_size, lambda_over, lambda_under, theta_queue)

        if cost < best_cost:
            best_cost = cost
            best_split = alloc

    return best_split, best_cost


def compute_cost(split, venues, order_size, lambda_over, lambda_under, theta_queue):
    """
    Computes the total expected cost for a given allocation split.

    Args:
        split (list[int]): Shares sent to each venue.
        venues (list): List of venue objects.
        order_size (int): Target shares to buy.
        lambda_over (float): Cost penalty per extra share bought.
        lambda_under (float): Cost penalty per unfilled share.
        theta_queue (float): Queue-risk penalty.

    Returns:
        float: Total expected cost of the split.
    """
    executed = 0
    cash_spent = 0.0

    for i in range(len(venues)):
        # Actual shares executed at this venue (cannot exceed available ask_size)
        exe = min(split[i], venues[i]['ask_sz_00'])
        executed += exe

        # Cash spent on executed shares
        cash_spent += exe * (venues[i]['ask_px_00']+ FEES)
        maker_rebate = max(split[i]-exe, 0) * REBATE
        cash_spent -= maker_rebate


    # Calculate penalties
    underfill = max(order_size - executed, 0)
    overfill = max(executed - order_size, 0)

    risk_pen = theta_queue * (underfill + overfill)
    cost_pen = lambda_under * underfill + lambda_over * overfill

    return cash_spent + risk_pen + cost_pen

def naive_best_ask(order_size, snapshots):
    """Naïve Best Ask: Fill order at the venue with the lowest ask price."""
    remaining = order_size
    cash_spent = 0
    for ts, venues in snapshots.items():
        if remaining <=0:
            break
        value = min(venues, key=lambda v: v['ask_px_00'])
        exe = min(remaining, value['ask_sz_00'])
        cash_spent += exe * (value['ask_px_00']+FEES)
        remaining -= exe
    return cash_spent

def cont_kukanov(order_size, snapshots, lambda_over, lambda_under, theta_queue):
    remaining_shares = order_size
    total_cash_spent = 0
    for ts, venues in snapshots.items():
        if remaining_shares <= 0:
            break
            
        if sum(v['ask_sz_00'] for v in venues) == 0:
            continue

        split, cost = allocate(remaining_shares, venues, lambda_over, lambda_under, theta_queue)
        
        if not split or cost == float('inf'):
            continue

        executed_this_step = 0
        for i, shares in enumerate(split):
            if shares > 0:
                actual_filled = min(shares, venues[i]['ask_sz_00'])
                executed_this_step += actual_filled
                total_cash_spent += actual_filled * (venues[i]['ask_px_00'] + FEES)
                maker_rebate = max(shares - actual_filled, 0) * REBATE
                total_cash_spent -= maker_rebate
        
        remaining_shares -= executed_this_step

    if remaining_shares > 0:
        underfill_penalty = lambda_under * remaining_shares + theta_queue * remaining_shares
    else:
        underfill_penalty = 0
    total_cost = total_cash_spent + underfill_penalty
    return total_cost

def tune_parameters(snapshots, order_size):
    p1 = list(np.random.uniform(0,1.0,10))
    p2 = list(np.random.uniform(0,1.0,10))
    p3 = list(np.random.uniform(0,1.0,10))
    best_cost = float('inf')
    best_params = []
    for lambda_over in p1:
        for lambda_under in p2:
            for theta_queue in p3:
                cost = cont_kukanov(order_size,snapshots,lambda_over, lambda_under, theta_queue)
                if cost < best_cost:
                    best_cost = cost
                    best_params = [float(lambda_over), float(lambda_under), float(theta_queue)]
    return best_cost, best_params

def vwap(order_size, snapshots):
    remaining_shares = order_size
    total_cash_spent = 0
    for ts, venues in snapshots.items():
        if remaining_shares <= 0:
            break
        total_volume = sum([v['ask_sz_00'] for v in venues])
        for v in venues:
            if remaining_shares <=0:
                break
            weight = v['ask_sz_00']/total_volume
            exe = min(int(remaining_shares*weight),v['ask_sz_00'])
            total_cash_spent += exe * (v['ask_px_00']+ FEES)
            remaining_shares -= exe
    return total_cash_spent


if __name__ == '__main__':
    consumer = KafkaConsumer(
        KAFKA_TOPIC,
        group_id=CONSUMER_GROUP_ID,
        bootstrap_servers=[KAFKA_BROKER],
        auto_offset_reset='earliest',
        enable_auto_commit=True,
        value_deserializer=lambda x: json.loads(x.decode('utf-8')),
        consumer_timeout_ms=20000
    )

    print(f"Consumer started, listening to topic: {KAFKA_TOPIC}")

    # Continuously consume messages
    snapshots = {}
    for message in consumer:
        print(f"Received: Topic={message.topic}, Partition={message.partition}, "
            f"Offset={message.offset}, Key={message.key}, Value={message.value}")
        value = message.value
        value['ask_px_00'] = float(value['ask_px_00'])
        value['ask_sz_00'] = int(value['ask_sz_00'])
        venues = snapshots.get(value['id'],[])
        venues.append(value)
        snapshots[value['id']] = venues

    print("Calculating SOR with Naive best Ask")
    naive_cash_spent = naive_best_ask(5000,snapshots)
    print(naive_cash_spent, naive_cash_spent/5000)
    vwap_cash_spent = vwap(5000,snapshots)
    print(vwap_cash_spent, vwap_cash_spent/5000)
    
    best_cost, best_params = tune_parameters(snapshots, 5000)
    print(best_cost, best_params, best_cost/5000)

    savings_vs_naive_best_ask = (1 - best_cost/naive_cash_spent)*1000
    print(savings_vs_naive_best_ask)

    savings_vs_vwap = (1 - best_cost/vwap_cash_spent)*1000
    print(savings_vs_vwap)
    
