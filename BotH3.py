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

game.ready("MyPythonBotV16")

"""
	ships info
"""
ship_status = {}
ship_move_compute = {}
ship_stock = {}
ship_previous_position = {}

returning_ship_moves_old_pos_new_pos = {}
"""
	map info
"""
pos_taken = {}
position_score = []
best_position_list = []
command_queue = []

MIN_MEAN_CELL_HALITE = 130
MAX_MEAN_CELL_HALITE = 240
COEF_MEAN_CELL_HALITE_RANGE = 0.5
COEF_HALITE_RETURN_THRESHOLD = 0.7
SCAN_SIZE = 3
BEST_POSITION_KEPT = 3
COEF_TURN_STOP_BUILD = 0.5
SHIP_BEFORE_DROPOFF = 15
MAX_DROPOFF = 1

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
max_ship = (10 + game_map.width * 0.3) * coef_mean_cell_halite
# Get the maximum of turn for this map
max_turn = MAX_TURN[game_map.width]


"""
	Scan the map to score each position
"""
def scan_map():
	position_score = []
	for x in range(game_map.width):
		for y in range(game_map.height):
			position = Position(x, y)
			position_score.append((position, compute_position_score(position)))
	position_score.sort(key=lambda element: element[1], reverse=True)
	return position_score

"""
	Compute the score of each a position
"""
def compute_position_score(position):
	sum = 0
	for x in range(-SCAN_SIZE, SCAN_SIZE+1):
		for y in range(-SCAN_SIZE, SCAN_SIZE+1):
			sum += game_map[game_map.normalize(Position(position.x + x, position.y + y))].halite_amount
	return sum

"""
	Get the best position of the map
"""
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
	
"""
	Return true if one of me ship is position
"""
def is_my_ship(position):
	for ship in me.get_ships():
		if ship.position == position:
			return True
	return False

"""
	Return a sorted list of (ship, distance_to_target)
"""
def distance_to_target(target, reversed=False):
	distance_to_target = []
	for ship in me.get_ships():
		distance_to_target.append((ship,game_map.calculate_distance(ship.position,target)))
	distance_to_target.sort(key=lambda element: element[1])
	if reversed:
	   distance_to_target.reverse()
	return distance_to_target
	
"""
	Return a sorted list of (ship, distance_to_target)
"""
def max_distance_to_dropoff():
	distance_to_dropoff = []
	for ship in me.get_ships(): 
		distance_to_dropoff.append((ship,game_map.calculate_distance(ship.position,get_closest_dropoff_position(ship.position))))
	distance_to_dropoff.sort(key=lambda element: element[1])
	distance_to_dropoff.reverse()
	return distance_to_dropoff[0][1]

"""
	Return list of emptiest ships
"""
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

"""
	counter_ship_on_shipyard
"""
def counter_ship_on_shipyard():
	if game_map[me.shipyard].is_occupied and not is_my_ship(me.shipyard.position):
		emptiest_ship_list = get_emptiest_ship()
		if emptiest_ship_list is None:
			return
		emptiest_ship_list.sort(key=lambda ship: game_map.calculate_distance(ship.position,me.shipyard.position))	
		kamikaze_ship = emptiest_ship_list[0]
		ship_status[kamikaze_ship.id] = "counter_ship_on_shipyard"
		
"""
	Compute the turn where all ship go to dropoff
"""
def end_game_management():
	if game.turn_number > 300 and len(me.get_ships()) > 0:
		max_dist = max_distance_to_dropoff()
		if game.turn_number > max_turn-max_dist-3:
			for ship in me.get_ships():
				ship_status[ship.id] = "end_game"

"""
	Get the closest dropoff to gieven position
"""
def get_closest_dropoff_position(position):
	closest_position = me.shipyard.position
	smallest_dist = game_map.calculate_distance(position, closest_position)
	
	for dropoff in me.get_dropoffs():
		tmp_dist = game_map.calculate_distance(position, dropoff.position)
		if tmp_dist < smallest_dist:
			closest_position = dropoff.position
			smallest_dist = tmp_dist
	
	return closest_position
	
"""
	Return truc is the ship is on a dropoff
"""
def is_ship_on_dropoff(ship):
	if ship.position == me.shipyard.position:
		return True
	else:
		for dropoff in me.get_dropoffs():
			if ship.position == dropoff.position:
				return True
	return False

"""
	Return true a ship has a given status
"""
def is_ship_with_status(status):
	for id in ship_status:
		if ship_status[id] == status:
			return True
	return False

"""
	Return truc is the ship is on a dropoff
"""
def dropoff_management():
	if (len(me.get_ships()) > SHIP_BEFORE_DROPOFF) \
	and (best_position_list[0] != me.shipyard.position) \
	and (len(me.get_dropoffs()) < MAX_DROPOFF) \
	and (is_ship_with_status("dropoff_builder") == False):
		
		logging.info("GO_DROPOFFFFFF !!!")
		closest_ship,_ = distance_to_target(best_position_list[0])[0]
		ship_status[closest_ship.id] = "dropoff_builder"

		
"""
	Get the movement cost of a given ship
"""
def get_ship_movement_cost(ship):
	return game_map[ship.position].halite_amount*0.1
		
"""
	Get the position with a given pos and move
"""
def get_new_position(pos, move):
	if 'o' in move:
		return pos
	else:
		return pos.directional_offset(move)

"""
	Get best returning move
"""
def compute_returning_moves(ship):
	moves = game_map.get_unsafe_moves(ship.position, get_closest_dropoff_position(ship.position))
	moves.sort(key=lambda move : game_map[get_new_position(ship.position, move)].halite_amount)
	final_move = None
	for move in moves:
		position = get_new_position(ship.position, move)
		# Check if the position is already booked
		if get_id_from_pos(position) in pos_taken:
			continue
		# Check if the position is not occupied
		if not game_map[position].is_occupied:
			final_move = move
			break
		# Check if the ship_on_cell is not mine
		if not me.has_ship(game_map[position].ship.id):
			continue
		ship_on_cell = game_map[position].ship
		# Check if the ship_on_cell is already compute
		if ship_on_cell.id in ship_move_compute:
			# Check if the ship_on_cell stay still
			if ship_move_compute[ship_on_cell.id] == ship_on_cell.stay_still():
				continue
			else:
				final_move = move
				break
		# Compute move for the ship_on_cell
		ship_on_cell_move = compute_move_to_free_space(ship_on_cell, ship)
		ship_move_compute[ship_on_cell.id] = ship_on_cell_move
		new_pos = get_new_position(ship_on_cell.position, ship_on_cell_move)
		pos_taken[get_id_from_pos(new_pos)] = 1
		logging.info("pos taken:{}x{}".format(new_pos.x, new_pos.y))
		command_queue.append(ship_on_cell.move(ship_on_cell_move))
		logging.info("ship_on_cell_move {}x{}: {}".format(ship_on_cell.position.x, ship_on_cell.position.y, ship_on_cell.move(ship_on_cell_move)))
		if ship_on_cell_move == (0,0):
			continue
		else:
			final_move = move
			break		
	if final_move is None:
		return (0,0)
	else:
		return final_move

"""
	Get best move to free space
"""
def compute_move_to_free_space(ship, ship_priority):
	final_move = None
	if ship.halite_amount < get_ship_movement_cost(ship):
		final_move = (0,0)
		return final_move
	if get_id_from_pos(ship_priority.position) not in pos_taken:
		final_move = game_map.get_unsafe_moves(ship.position, ship_priority.position)[0]
		return final_move
	for pos in ship_on_cell_move.position.get_surrounding_cardinals():
		if get_id_from_pos(pos) in pos_taken:
			continue
		if game_map[position].is_occupied:
			# Check if the ship_on_cell is not mine
			if not me.has_ship(game_map[position].ship.id):
				continue
			ship_on_cell = game_map[position].ship
			if ship_on_cell.id == ship_priority.id:
				continue
			# Check if the ship_on_cell is already compute
			if ship_on_cell.id not in ship_move_compute:
				continue
			if ship_move_compute[ship_on_cell.id] == ship_on_cell.stay_still():
				continue
		final_move = game_map.get_unsafe_moves(ship.position, pos)[0]
		return final_move	
	final_move = (0,0)
	return final_move
	
"""
	Get the id from the position
"""
def get_id_from_pos(pos):
	norm_pos = game_map.normalize(pos)
	return norm_pos.x+(norm_pos.y*game_map.width)

"""
	Get the position from the id
"""	
def get_pos_from_id(id):
	return Position(id%game_map.width, (id-(id%game_map.width))/game_map.width)
	
"""
	Main loop
"""
while True:
	game.update_frame()
	me = game.me
	game_map = game.game_map
	command_queue = []
	ship_move_compute = {}
	pos_taken = {}
	
	ship_returning = []
	ship_exploring = []
	ship_collecting = []
	ship_other = []
	
	if game.turn_number == 1:
		position_score = scan_map()
		best_position_list = get_best_position()
		logging.info("best_position_list:{}".format(best_position_list))
	
	ship_to_remove = []
	for id in ship_status:
		if not me.has_ship(id):
			ship_to_remove.append(id)
	
	for id in ship_to_remove:
		del ship_status[id]
		if id in ship_move_compute:
			del ship_move_compute[id]
		if id in ship_stock:
			del ship_stock[id]
		if id in ship_previous_position:
			del ship_previous_position[id]

	
	counter_ship_on_shipyard()
	dropoff_management()
	end_game_management()
	
	for ship in me.get_ships():
		if ship.id not in ship_status:
			ship_status[ship.id] = "exploring"
		if ship_status[ship.id] == "returning":
			ship_returning.append(ship)
		elif ship_status[ship.id] == "exploring":
			ship_exploring.append(ship)
		elif ship_status[ship.id] == "collecting":
			ship_collecting.append(ship)
		else:
			ship_other.append(ship)
	
	ship_returning.sort(key=lambda ship : game_map.calculate_distance(ship.position, get_closest_dropoff_position(ship.position)))	


	# Start returning ship management --------------------------------
	for ship in ship_returning:
		if ship.id in ship_move_compute:
			#logging.info("Ship already compute")
			continue
		if is_ship_on_dropoff(ship):
			ship_status[ship.id] = "exploring"
			continue
		move = compute_returning_moves(ship)
		new_pos = get_new_position(ship.position, move)
		pos_taken[get_id_from_pos(new_pos)] = 1
		logging.info("pos taken:{}x{}".format(new_pos.x, new_pos.y))
		ship_move_compute[ship.id] = move
		command_queue.append(ship.move(move))
		logging.info("ship {}x{}: {}".format(ship.position.x, ship.position.y, ship.move(move)))
	 # End returning ship management-----------------------------------------------------------
	

	for ship in me.get_ships():
		
		if ship.id in ship_move_compute:
			#logging.info("Ship already compute")
			continue
		
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
		if ship_status[ship.id] == "counter_ship_on_shipyard":
			if game_map.calculate_distance(ship.position, me.shipyard.position) == 1:
				move = game_map.get_unsafe_moves(ship.position, me.shipyard.position)[0]
				ship_status[ship.id] = "exploring"
			else:
				move = game_map.naive_navigate(ship, me.shipyard.position)
			ship_move_compute[ship.id] = ship.move(move)
			command_queue.append(ship.move(move))
			continue
		elif ship_status[ship.id] == "end_game":
			if game_map.calculate_distance(ship.position, get_closest_dropoff_position(ship.position)) == 1:
				move = game_map.get_unsafe_moves(ship.position, get_closest_dropoff_position(ship.position))[0]
			else:
				move = game_map.naive_navigate(ship, get_closest_dropoff_position(ship.position))
			ship_move_compute[ship.id] = ship.move(move)
			command_queue.append(ship.move(move))
			continue
		elif ship_status[ship.id] == "dropoff_builder":
			logging.info("dropoff_builder management")
			build_pos = best_position_list[0]
			if game_map[best_position_list[0]].has_structure:
				build_pos = best_position_list[2]
			if ship.position == build_pos:
				if me.halite_amount + game_map[build_pos].halite_amount + ship.halite_amount >= 4000:
					logging.info("make dropff")
					ship_move_compute[ship.id] = ship.make_dropoff()
					command_queue.append(ship.make_dropoff())
					continue
				else:
					logging.info("wait to dropff")
					ship_move_compute[ship.id] = ship.stay_still()
					command_queue.append(ship.stay_still())
					continue
			else:
				move = game_map.naive_navigate(ship, build_pos)
				ship_move_compute[ship.id] = ship.move(move)
				command_queue.append(ship.move(move))
				continue
		elif ship_status[ship.id] == "returning":
			if is_ship_on_dropoff(ship):
				ship_status[ship.id] = "exploring"
			else:
				move = game_map.naive_navigate(ship, get_closest_dropoff_position(ship.position))
				ship_move_compute[ship.id] = ship.move(move)
				command_queue.append(ship.move(move))
				continue
		elif ship.halite_amount >= constants.MAX_HALITE*COEF_HALITE_RETURN_THRESHOLD:
			ship_status[ship.id] = "returning"
		elif ship_status[ship.id] == "collecting":
			ship_move_compute[ship.id] = ship.stay_still()
			command_queue.append(ship.stay_still())
			ship_status[ship.id] = "exploring"
			continue
		# End status management -------------------------------------------
		
		if ship.halite_amount < movement_cost :
			ship_move_compute[ship.id] = ship.stay_still()
			command_queue.append(ship.stay_still())
			continue
		
		# Check all move
		possible_position_list = []
		for possible_position in ship.position.get_surrounding_cardinals():	   
			if game_map[possible_position].is_occupied:
				continue
			if get_id_from_pos(possible_position) in pos_taken:
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
			ship_move_compute[ship.id] = ship.stay_still()
			command_queue.append(ship.stay_still())
		else:
			ship_move_compute[ship.id] = ship.move(ship_move)
			command_queue.append(ship.move(ship_move))
		
		ship_previous_position[ship.id] = ship.position
		

	# Check space arround shipyard
	nb_free_cell = 0
	for possible_position in me.shipyard.position.get_surrounding_cardinals():
		if not game_map[possible_position].is_occupied:
			nb_free_cell += 1

	# Generate new ship
	if nb_free_cell >= 1 \
	and not is_ship_with_status("dropoff_builder") \
	and not get_id_from_pos(me.shipyard.position) in pos_taken \
	and len(me.get_ships()) < max_ship \
	and game.turn_number <= max_turn*COEF_TURN_STOP_BUILD \
	and me.halite_amount >= constants.SHIP_COST \
	and not game_map[me.shipyard].is_occupied:
		command_queue.append(game.me.shipyard.spawn())

	# Send your moves back to the game environment, ending this turn.
	game.end_turn(command_queue)

