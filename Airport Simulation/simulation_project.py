# -*- coding: utf-8 -*-
"""Simulation_Project.ipynb

## Security Area simulation model

Here we enumerate some steps to complete the modeling of the securoty area of an airport:

1. Conceptual Model
2. Data analysis and approximation of processing time in the check in area and the terminal area
3. Build an initial model of the present state
4. Verify and validate
5. Test performance under increased demand
"""

#!pip install simpy
#!pip install -U arrow
import simpy
import numpy as np
import pandas as pd
import arrow
#from google.colab import drive
#drive.mount('/content/drive/')

flights = pd.read_csv("Flight1Day.csv")
nflights = flights.shape[0]
flights.head()

"""## Simulation Time

Since Simpy has no features to include actual dates and times. We can convert everything into seconds elapsed from the first event. In the cell below, we write a function to :
1. Extract time from the columns `Passenger Start time` and `Flight Departure Time`.
2. Set the first start time to 0 seconds and write function to calculate number of seconds from that time.
"""

zero = arrow.get(flights['Passenger Start Time'][0], 'M/D/YYYY H:mm')
flights['Start_timestamp'] = flights['Passenger Start Time'].apply(lambda x: ((arrow.get(x, 'M/D/YYYY H:mm')).timestamp - zero.timestamp))
flights['Departure_timestamp'] = flights['Flight Departure Time'].apply(lambda x: ((arrow.get(x, 'M/D/YYYY H:mm')).timestamp - zero.timestamp))

flights.head()

#Test data for verification with only 10 passengers
flights = flights.iloc[0:3]
flights['Num Passengers'][0] = 5
flights['Num Passengers'][1] = 5
flights['Num Passengers'][2] = 5
nflights = 3
flights

ID_CHECK_TIME = 'np.random.triangular(5.06, 10.00, 19.80)'
ID_FAIL_PROB = 0.12
BODY_CHECK_FAIL_RATE = 0.1219
BAG_CHECK_FAIL_RATE = 0.1253
ADV_BAG_CHECK_FAIL_RATE = 0.05
ADV_BODY_CHECK_FAIL_RATE = 0.05
REVEST_TIME = 'np.random.triangular(60.34, 76.56, 109.71)'
DIVEST_TIME = 'np.random.triangular(10.27, 27.22, 39.58)'
PER_XP_PASSENGERS = 0.4
DIVESTING_CAP = 3
REVESTING_CAP = 3
N_REGULAR_LANES = 4
N_EXPRESS_LANES = 2
SAFE_DISTANCE = 2 #Safe distance between passengers = 2ft
class Security_Lane(object):
    def __init__(self, env, num_divest_stations, mounted_scanners, advanced_bagscanners, advanced_bodyscanners, num_revest_stations):
        self.env = env
        self.mounted_scanners = mounted_scanners
        self.advanced_bagscanners = advanced_bagscanners
        self.advanced_bodyscanners = advanced_bodyscanners
        self.baggage_scanner1 = simpy.Resource(env, 1 + mounted_scanners*1)
        self.revest_station1 = simpy.Resource(env, num_revest_stations)
        self.divest_station1 = simpy.Resource(env, num_divest_stations)
        self.divest_station2 = simpy.Resource(env, num_divest_stations)
        #self.divest_station_Qchanged = env.event()
        self.baggage_scanner2 = simpy.Resource(env, 1 + mounted_scanners*1)
        self.revest_station2 = simpy.Resource(env, num_revest_stations)
        self.bodyscanner = simpy.Resource(env, 1)
        self.manual_bag_checker = simpy.Resource(env, 1)
        self.manual_body_checker = simpy.Resource(env, 1)
    
    def Num_in_lane(self):
        return [len(self.revest_station1.queue), len(self.revest_station2.queue)]
    
    def divest(self):
        yield self.env.timeout(eval(DIVEST_TIME))

    def bagscan(self, passenger_state):
        ntrays = passenger_state['n_trays']
        if ntrays == 1:
            sc_time = np.random.uniform(10, 20)
        elif ntrays == 2:
            sc_time = np.random.uniform(16, 22)
        elif ntrays == 3:
            sc_time = np.random.uniform(21, 24)
        else:
            sc_time = np.random.uniform(20, 24)
        if self.advanced_bagscanners == True:
            sc_time = 5*ntrays
        yield self.env.timeout(sc_time)
    def bodyscan(self):
        if self.advanced_bodyscanners == False:
            bs_time = np.random.triangular(5.03, 9.12, 11.94)
        else:
            bs_time = 5
        yield self.env.timeout(bs_time)
    
    def manual_bagscan(self):
        yield self.env.timeout(np.random.triangular(15.7,39.5,58.7))
    def manual_bodyscan(self):
        yield self.env.timeout(np.random.triangular(35.3,39.5,44.8))
    def revest(self):
        yield self.env.timeout(eval(REVEST_TIME))
     


class Security_area(object):
    """Security Area has a limited number of lanes (``NUM_LANES``) and 
    equal number of identity check areas ID_CHECKS.
    Passengers choose one of the ID check stations to queue up in front of 
    and choose one lane to go into. As long as they are in queue waiting, 
    they check the other queue lengths and change to the queue that is shorter.
    """
    def __init__(self, env, num_counters):
        self.env = env
        self.id_check_counter = simpy.Resource(env, num_counters)
    def id_check(self, passenger_state):
        """The id_checking process. It takes a ``passenger`` processes and checks id."""
        yield self.env.timeout(eval(ID_CHECK_TIME))
    def choose_lane(self, passenger_state):
      """Choose the lane with the shortest entrance queue"""
      typelane = passenger_state['typelane']
      choice = np.argmin([lane.Num_in_lane() for lane in eval(typelane + 'Lane')])
      return (int(choice/2), choice%2)
    def get_min_lanes(self, passenger_state):
      """Get the least no of people in any queue"""
      typelane = passenger_state['typelane']
      min_no = np.min([lane.Num_in_lane() for lane in eval(typelane+'Lane')])
      return min_no

class Departure_area(object):
    """
    Departure area has `num_checkin_counters` check-in counters, 
    `num_kiosks` kiosks and `num_bagdrops` bagdrop stations
    """
    def __init__(self, env):
        self.env = env
        self.departure_counters = simpy.Resource(env, capacity = 30)
    def process_departure(self, passenger_state):
        if passenger_state['airline_type'] == 'Business':
            yield env.timeout(np.random.uniform(3.5, 5.5)*60)
        else:
            yield env.timeout(np.random.uniform(7,9)*60)
        
class Terminal_area(object):
    """Terminal area has two terminals (each 750 ft long) 
        and a connecting concourse (1000 ft long on each direction). 
        If a moving sidewalk is present in the concourse then it could take on
        lengths 300, 500 or 900 ft"""
    def __init__(self, env, has_moving_sidewalk, length):
        self.env = env
        self.has_moving_sidewalk = has_moving_sidewalk
        if self.has_moving_sidewalk == True:
            self.moving_sidewalk = simpy.Resource(env, capacity = int(length/(SAFE_DISTANCE+1)))
        else:
            self.moving_sidewalk = simpy.Resource(env, capacity = 500)
    def move_in_terminal(self):
        #Walk in concourse
        if self.has_moving_sidewalk == True:
            delay_time = ((1000-self.length)/4.6) + (self.length/9.6) + (np.random.choice([750, 400], p = [0.5, 0.5]))/4.6
        else:
            delay_time = (1000 + np.random.choice([750, 400], p = [0.5, 0.5]))/4.6
        yield env.timeout(delay_time)

def source(env, departure_hall, security_area, terminal_area):
    """Source generates passengers as per flight schedule 2 hours before departure:
        Read from Flights1Day
    """
    for i in range(nflights):
      flight_type = np.random.choice(["Business", "Budget"], p = [0.607, 0.393])
      delay = flights['Start_timestamp'][i] - env.now
      if delay > 0: yield env.timeout(delay)
      for j in range(flights['Num Passengers'][i]):
        #Random Delay
        #Assign nbags
        states = {}
        nt = np.random.choice(5, p = [0, 0.20247, 0.3983, 0.2936, 0.10563])
        states['n_trays'] = nt
        states['airline_type'] = flight_type
        states['flight_no'] = i
        c = Passenger(env, 'Passenger%02d' % (i*1000 + j+1), states, departure_hall, security_area, terminal_area)
        yield env.timeout(0)

    
class Passenger(object):
    def __init__(self, env, name, state_var_dict, departure_hall, security_area, terminal_area):
        self.env = env
        self.name = name
        self.states = state_var_dict
        self.departure_hall = departure_hall
        self.security_area = security_area
        self.terminal_area = terminal_area
        self.change_lanes = env.event()
        self.process_run = env.process(self.run_through(env))
        self.exit_passenger = env.process(self.gen_flight_departure(env))
    
    # def change_lanes(self, env):
    #     cap_change = simpy.AnyOf(env, [lane.divest_station_Qchanged for lane in RegularLane])
    #     yield cap_change
    #     if self.security_area.get_min_lanes(self.states) < eval('lane.divest_station['+str(self.states['sublane'])+'].request()')


    def gen_flight_departure(self, env):
        try:
            yield env.timeout(flights['Departure_timestamp'][self.states['flight_no']] - env.now)
            self.process_run.interrupt(str(env.now)+ ', '+ str(self.name)+':Flight Departed')
        except:
            pass
            
    
    def run_through(self, env):
        try:
            print('%7.4f %s: Generated' % (env.now, self.name))
            
            #Random delay before arriving at the airport
            #80% arrive by personal car and walk to departure hall
            #20% dropped off at the deprarture hall curbside
            arrival_bucket = np.random.choice(12, p = [0.01, 0.07, 0.12, 0.16, 0.2, 0.1, 0.09, 0.08, 0.09, 0.05, 0.03, 0])
            #time to arrival at airport
            tua = 600*arrival_bucket + np.random.uniform(0, 10*60)
            yield env.timeout(tua)
            if np.random.uniform() <= 0.8:
                #walk from parking lot
                #People typically walk at 4.6 ft/s
                ttw = np.random.uniform(1000, 2500)/4.6
                yield env.timeout(ttw) 
            print('%7.4f %s: Arrived at departure hall curbside'%(env.now, self.name))
            self.states['sublane'] = 0
            #Process 1: Check-in
            with self.departure_hall.departure_counters.request() as req:
                yield req
                print('%7.4f %s: Reached check-in counter' % (env.now, self.name))
                yield env.process(self.departure_hall.process_departure(self.states))
                print('%7.4f %s: Finished check-in' % (env.now, self.name))
            #Process 2: ID-Check
            with self.security_area.id_check_counter.request() as req:
                yield req
                print('%7.4f %s: Reached id-check counter' % (env.now, self.name))
                yield env.process(self.security_area.id_check(self.states))
            if np.random.uniform() <= ID_FAIL_PROB:
                print('%7.4f %s: Failed id-check' % (env.now, self.name))
                with self.departure_hall.departure_counters.request() as req:
                    yield req
                    print('%7.4f %s:REDO: Reached check-in counter' % (env.now, self.name))
                    yield env.process(self.departure_hall.process_departure(self.states))
                    #Process 2: ID-Check
                with self.security_area.id_check_counter.request() as req:
                    yield req
                    print('%7.4f %s: REDO: Reached id-check counter' % (env.now, self.name))
                    yield env.process(self.security_area.id_check(self.states))
            print('%7.4f %s: Completed id-check' % (env.now, self.name))
            #Process 3: Choose security lane and finish divesting
            self.states['typelane'] = np.random.choice(["Regular", "Express"], p = [1-PER_XP_PASSENGERS, PER_XP_PASSENGERS])
            print('%7.4f %s: Is a %s passenger'%(env.now, self.name, self.states['typelane']))
            self.states['chosen_lane'], self.states['sublane'] = self.security_area.choose_lane(self.states)
            Lane = eval(self.states['typelane']+'Lane['+str(self.states['chosen_lane'])+']')
            print('%7.4f %s: Initially chose %sLane %d, station %d'%(env.now, self.name, self.states['typelane'], self.states['chosen_lane'], self.states['sublane']))
            with eval('Lane.divest_station'+str(self.states['sublane']+1)).request() as req:
                yield req
                yield env.process(Lane.divest())
            print('%7.4f %s: Completed divesting' % (env.now, self.name))
            #Process 4: Parallel finish bagscan and body scan and check
            bagp = env.process(self.bagcheck(env, eval('Lane.baggage_scanner'+str(self.states['sublane']+1)), Lane))
            bodyp = env.process(self.bodycheck(env, Lane))
            yield bagp & bodyp
            #Process 5: Finish revesting
            with eval('Lane.revest_station'+str(self.states['sublane']+1)).request() as req:
                yield req
                yield env.process(Lane.revest())
            print('%7.4f %s: Completed revesting' % (env.now, self.name))
            #Process 6: Move through terminal
            if self.terminal_area.has_moving_sidewalk:
                with self.terminal_area.moving_sidewalk.request() as req:
                    yield req
                    print('%7.4f %s: Using Moving sidewalk' % (env.now, self.name))
            print('%7.4f %s: Moving in terminal' % (env.now, self.name))
            yield env.process(self.terminal_area.move_in_terminal())
            print('%7.4f %s: Boarded flight' % (env.now, self.name))
        except simpy.Interrupt as i:
            print('%7.4f %s: Passenger interrupted: %s' % (env.now, self.name, i.cause))
    
    def bagcheck(self, env, scanner, lane):
        with scanner.request() as reqscan:
            yield reqscan
            yield env.process(lane.bagscan(self.states))
        print('%7.4f %s: Bags have been scanned' % (env.now, self.name))
    
    def bodycheck(self, env, lane):
        with lane.bodyscanner.request() as reqselfscan:
            yield reqselfscan
            print('%7.4f %s: Using body scanner' % (env.now, self.name))
            yield env.process(lane.bodyscan())
        print('%7.4f %s: Body has been scanned' % (env.now, self.name))
        if lane.advanced_bodyscanners: fail = ADV_BODY_CHECK_FAIL_RATE
        else: fail = BODY_CHECK_FAIL_RATE 
        if np.random.uniform() <= fail:
            print('%7.4f %s: Body scan failed' % (env.now, self.name))
            with lane.manual_body_checker.request() as reqselfscan:
                yield reqselfscan
                print('%7.4f %s: Manual Body scan in progress' % (env.now, self.name))
                yield env.process(lane.manual_bodyscan())
                print('%7.4f %s: Manual Body scan completed' % (env.now, self.name))
        

# Setup and start the simulation
print('Airport Simulation')
np.random.seed(123)
env = simpy.Environment()

# Start processes and run
#create idcheck, divest and revest as this kind of resource
departure_hall = Departure_area(env)
main_security_area = Security_area(env, N_REGULAR_LANES+N_EXPRESS_LANES)
terminal_area = Terminal_area(env, False, 0)
RegularLane = [Security_Lane(env, DIVESTING_CAP, False, False, False, REVESTING_CAP) for i in range(N_REGULAR_LANES)]
ExpressLane = [Security_Lane(env, DIVESTING_CAP, False, False, False, REVESTING_CAP) for i in range(N_EXPRESS_LANES)]
env.process(source(env, departure_hall, main_security_area, terminal_area))
env.run()

