#!/usr/bin/env python3
# Python 3.6

import hlt
from hlt import constants
from hlt.positionals import Direction, Position

import random
import logging


game = hlt.Game()
game_map = game.game_map

MEAN_CELL_HALITE = sum([cell.halite_amount for raw in game_map._cells for cell in raw ]) / (game_map.width*game_map.height)
MAX_TURN = {\
	32:401,\
	40:426,\
	48:451,\
	56:476,\
	64:501}

game.ready("MyPythonBotV15_add_dropoff_management")

ship_status = {}
ship_move_compute = {}
ship_stock = {}
ship_previous_position = {}

position_score = []
best_position_list = []

MIN_MEAN_CELL_HALITE = 130
MAX_MEAN_CELL_HALITE = 240
COEF_MEAN_CELL_HALITE_RANGE = 0.5
COEF_HALITE_RETURN_THRESHOLD = 0.7
SCAN_SIZE = 4
BEST_POSITION_KEPT = 1

min_coef_mean_cell_halite = 1.0 - COEF_MEAN_CELL_HALITE_RANGE/2
x = 0

# Compute the mean cell halite coeficient
coef_mean_cell_halite = 0
if MEAN_CELL_HALITE < MIN_MEAN_CELL_HALITE:
	coef_mean_cell_halite = 1.0 - COEF_MEAN_CELL_HALITE_RANGE/2
elif MEAN_CELL_HALITE > MAX_MEAN_CELL_HALITE:
	coef_mean_cell_halite = 1.0 + COEF_MEAN_CELL_HALITE_RANGE/2
else:
	x = (MEAN_CELL_HALITE-MIN_MEAN_CELL_HALITE) / (MAX_MEAN_CELL_HALITE-MIN_MEAN_CELL_HALITE)
	coef_mean_cell_halite = min_coef_mean_cell_halite + COEF_MEAN_CELL_HALITE_RANGE*x

# Compute the maximum of ship
max_ship = (10 + game_map.width * 0.25) * coef_mean_cell_halite
# Get the maximum of turn for this map
max_turn = MAX_TURN[game_map.width]


def scan_map():
	position_score = []
	for x in range(game_map.width):
		for y in range(game_map.height):
			position = Position(x, y)
			position_score.append((position, compute_position_score(position)))
	position_score.sort(key=lambda element: element[1], reverse=True)
	return position_score

def compute_position_score(position):
	sum = 0
	for x in range(-SCAN_SIZE, SCAN_SIZE+1):
		for y in range(-SCAN_SIZE, SCAN_SIZE+1):
			sum += game_map[game_map.normalize(Position(position.x + x, position.y + y))].halite_amount
	return sum

def get_best_position():
	best_position_list = []
	for position,score in position_score:
		if len(best_position_list) < BEST_POSITION_KEPT:
			is_far_enough = True
			for best_position in best_position_list:
				if game_map.calculate_distance(position, best_position) < SCAN_SIZE*2:
					is_far_enough = False
					break

			if is_far_enough:
				best_position_list.append(position)
		else:
			break;
	return best_position_list

# Return true if one of me ship is position
def is_my_ship(position):
	for ship in me.get_ships():
		if ship.position == position:
			return True
	return False

# Return a sorted list of (ship, distance_to_target)
def distance_to_target(target, reversed=False):
	distance_to_target = []
	for ship in me.get_ships():
		distance_to_target.append((ship,game_map.calculate_distance(ship.position,target)))
	distance_to_target.sort(key=lambda element: element[1])
	if reversed:
	   distance_to_target.reverse()
	return distance_to_target

# Return list of emptiest ships
def get_emptiest_ship():
	if me.get_ships() is None or len(me.get_ships()) == 0:
		return None
	emptiest_ship_list = []
	emptiest_ship_list.append(list(me.get_ships())[0])
	for ship in me.get_ships():
		if ship.halite_amount < emptiest_ship_list[0].halite_amount:
			emptiest_ship_list = []
			emptiest_ship_list.append(ship)
		elif ship.halite_amount == emptiest_ship_list[0].halite_amount:
			emptiest_ship_list.append(ship)
	
	return emptiest_ship_list	

def counter_ship_on_shipyard():
	if game_map[me.shipyard].is_occupied and not is_my_ship(me.shipyard.position):
		emptiest_ship_list = get_emptiest_ship()
		emptiest_ship_list.sort(key=lambda ship: game_map.calculate_distance(ship.position,me.shipyard.position))	
		kamikaze_ship = emptiest_ship_list[0]
		ship_status[kamikaze_ship.id] = "counter_ship_on_shipyard"
		

def end_game_management():
	if game.turn_number > 300 and len(me.get_ships()) > 0:
		dists = distance_to_target(me.shipyard.position, True)
		max_dist = dists[0][1]
		if game.turn_number > max_turn-max_dist-3:
			for ship in me.get_ships():
				ship_status[ship.id] = "end_game"


while True:
	game.update_frame()
	me = game.me
	game_map = game.game_map
	command_queue = []
	
	if game.turn_number % 20 == 1:
		position_score = scan_map()
		#logging.info("position_score:{}".format(position_score))
		best_position_list = get_best_position()
		logging.info("best_position_list:{}".format(best_position_list))
	
	counter_ship_on_shipyard()
	end_game_management()
	
	for ship in me.get_ships():
		
		if ship.id not in ship_previous_position:
			ship_previous_position[ship.id] = ship.position
			ship_stock[ship.id] = 0
		else:	   
			if ship_previous_position[ship.id] == ship.position and not ship_status[ship.id] == "collecting":
				if ship.id in ship_stock:
					ship_stock[ship.id] += 1
				else:
					ship_stock[ship.id] = 1
			else:
				ship_stock[ship.id] = 0
	
		movement_cost = game_map[ship.position].halite_amount*0.1
		ship_move = None
		
		# Start status management ------------------------------------------
		if ship.id not in ship_status:
			ship_status[ship.id] = "exploring"

		if ship_status[ship.id] == "counter_ship_on_shipyard" or ship_status[ship.id] == "end_game":
			if game_map.calculate_distance(ship.position, me.shipyard.position) == 1:
				move = game_map.get_unsafe_moves(ship.position, me.shipyard.position)[0]
			else:
				move = game_map.naive_navigate(ship, me.shipyard.position)
			command_queue.append(ship.move(move))
			continue
			
		if ship_status[ship.id] == "returning":
			if ship.position == me.shipyard.position:
				ship_status[ship.id] = "exploring"
			else:
				move = game_map.naive_navigate(ship, me.shipyard.position)
				command_queue.append(ship.move(move))
				continue
		elif ship.halite_amount >= constants.MAX_HALITE*COEF_HALITE_RETURN_THRESHOLD:
			ship_status[ship.id] = "returning"
		elif ship_status[ship.id] == "collecting":
			command_queue.append(ship.stay_still())
			ship_status[ship.id] = "exploring"
			continue
		# End status management -------------------------------------------
		
		
		
		
		if ship.halite_amount < movement_cost :
			command_queue.append(ship.stay_still())
			continue
		
		# Check all move
		possible_position_list = []
		for possible_position in ship.position.get_surrounding_cardinals():	   
			if game_map[possible_position].is_occupied:
				continue

			# Ship stock or at the base
			if me.shipyard.position == ship.position or ship_stock[ship.id] >= 4:
				possible_position_list.append((possible_position,game_map[possible_position].halite_amount))
			else:
				# Move worth it ?
				if game_map[possible_position].halite_amount*0.25-movement_cost*3 >= game_map[ship.position].halite_amount*0.25 and possible_position != me.shipyard.position:
					possible_position_list.append((possible_position,game_map[possible_position].halite_amount))
					if game_map[possible_position].halite_amount > 30 :
						ship_status[ship.id] = "collecting"

		# Find best move
		if len(possible_position_list) > 0:
			possible_position_list.sort(key=lambda element: element[1], reverse=True)
			best_position = None
			equal_position_list = []
			for position in possible_position_list:
				if position[1] == possible_position_list[0][1]:
					equal_position_list.append(position[0])

			# If more than two move with same score, random
			if len(equal_position_list) > 1:
				best_position = random.choice(equal_position_list)
			else:
				best_position = possible_position_list[0][0]
			
			ship_move = game_map.naive_navigate(ship, best_position)   
		# Store the move for that ship
		if ship_move == None:
			command_queue.append(ship.stay_still())
		else:
			command_queue.append(ship.move(ship_move))
		
		ship_previous_position[ship.id] = ship.position
		

	# Check space arround shipyard
	nb_free_cell = 0
	for possible_position in me.shipyard.position.get_surrounding_cardinals():
		if not game_map[possible_position].is_occupied:
			nb_free_cell += 1

	# Generate new ship
	if nb_free_cell >= 2\
	and len(me.get_ships()) < max_ship\
	and game.turn_number <= max_turn/2\
	and me.halite_amount >= constants.SHIP_COST\
	and not game_map[me.shipyard].is_occupied:
		command_queue.append(game.me.shipyard.spawn())

	# Send your moves back to the game environment, ending this turn.
	game.end_turn(command_queue)

