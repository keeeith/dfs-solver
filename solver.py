# Fanduel Solver 
# Based on: 
# https://github.com/swanson/degenerate
# https://github.com/mrnitrate/Draftkings-Optimal-Lineup-Generator

from ortools.linear_solver import pywraplp
import csv

class Player:

    def __init__(self, opts):   
        self.id = opts['Id']
        self.position = opts['Position'].upper()
        self.name = opts['First Name'] + " " + opts['Last Name']
        self.salary = int(opts['Salary'])
        #Sometimes projections have bad or missing projection for players, so we need to check
        try:
            self.projected = float(opts['FPPG'])
        except:
            self.projected = float(0)
        self.team = opts['Team']
        self.opponent = opts['Opponent']
        self.lock = int(opts['Lock']) > 0
        self.ban = int(opts['Lock']) < 0
        
    def __repr__(self):
        return "{0},{1},{2},${3},{4}".format(self.position, \
                                    self.name, \
                                    self.team, \
                                    self.salary, \
                                    self.projected,
                                    "LOCK" if self.lock else "")
        
    def export_csv(self):
        return [self.position,self.name,self.team,self.salary,self.projected]

class Roster:
    POSITION_ORDER = {
        "QB": 0,
        "WR": 1,
        "RB": 2,
        "TE": 3,
        "K": 4,
        "D": 5,
    }

    def __init__(self):
        self.players = []

    def add_player(self, player):
        self.players.append(player)

    def spent(self):
        return sum(map(lambda x: x.salary, self.players))

    def projected(self):
        return sum(map(lambda x: x.projected, self.players))

    def position_order(self, player):
        return self.POSITION_ORDER[player.position]

    def sorted_players(self):
        return sorted(self.players, key=self.position_order)

    def __repr__(self):
        s = '\n'.join(str(x) for x in self.sorted_players())
        s += "\n\nProjected Score: %s" % self.projected()
        s += "\tCost: $%s" % self.spent()
        return s

SALARY_CAP = 60000

POSITION_LIMITS = [
    ["QB", 1],
    ["RB", 2],
    ["WR", 3],
    ["TE", 1],  
    ["K",  1],
    ["D",  1]
]

ROSTER_SIZE = 9
TEAM_MAX = 4

def write_bulk_import_csv(rosters):
    with open('test.csv', 'wb') as csvfile:
        writer = csv.writer(csvfile,delimiter=',',quotechar='"',quoting=csv.QUOTE_NONNUMERIC)
        for roster in rosters:
            writer.writerow([x.name for x in roster.sorted_players()])
            
def run():
    solver = pywraplp.Solver('FD', pywraplp.Solver.CBC_MIXED_INTEGER_PROGRAMMING)
    all_players = []
    with open('Player List 09-11-2016.csv', 'rb') as csvfile:
        csvdata = csv.DictReader(csvfile, skipinitialspace=True)
        for row in csvdata:
            all_players.append(Player(row))

    variables = []

    for player in all_players:
        if player.lock:
            variables.append(solver.IntVar(1, 1, player.id))
        elif player.ban:
            variables.append(solver.IntVar(0, 0, player.id))
        else:      
            variables.append(solver.IntVar(0, 1, player.id))
        
    objective = solver.Objective()
    objective.SetMaximization()
    
    #
    # Add projected points for each player
    #
    for i, player in enumerate(all_players):
        objective.SetCoefficient(variables[i], player.projected)
    
    #
    # Add salary cap and salary for each player
    
    salary_cap = solver.Constraint(0, SALARY_CAP)
    for i, player in enumerate(all_players):
        salary_cap.SetCoefficient(variables[i], player.salary)
    
    #
    # Add min number of different teams players must be drafted from constraint
    #
    team_names = set([o.team for o in all_players])
    teams = []
    for team in team_names:
        teams.append(solver.IntVar(0, 1, team))
    solver.Add(solver.Sum(teams)>=6)
    
    for i, team in enumerate(team_names):
        ids, players_by_team = zip(*filter(lambda (x,_): x.team in team, zip(all_players, variables)))
        solver.Add(teams[i]<=solver.Sum(players_by_team))
    #
    # Add defense cant play against any offensive player constraint
    #
    o_players = filter(lambda x: x.position in ['QB','WR','RB','TE'], all_players)
    opps_team_names= set([o.opponent for o in o_players])
    teams_obj = filter(lambda x: x.position == 'D' , all_players)
    teams = set([o.team for o in teams_obj])     
    
    for opps_team in team_names:
        if opps_team in teams :
            ids, players_by_opps_team = zip(*filter(lambda (x,_): x.position in ['QB','WR','RB','TE'] and x.opponent in opps_team, zip(all_players, variables)))
            idxs, defense = zip(*filter(lambda (x,_): x.position == 'D' and x.team in opps_team, zip(all_players, variables)))
            solver.Add(solver.Sum(1-x for x in players_by_opps_team)+solver.Sum(1-x for x in defense)>=1)

    #
    # Add QB stacking (at least 1 wr or te on same team as QB) constraint
    #
    offense_team_names = set([o.team for o in o_players])
    for o_team in offense_team_names:
        ids, players_by_team = zip(*filter(lambda (x,_): x.position in ['WR','TE'] and x.team == o_team, zip(all_players, variables)))
        idxs, qb = zip(*filter(lambda (x,_): x.position == 'QB' and x.team == o_team, zip(all_players, variables)))
        solver.Add(solver.Sum(players_by_team)>=solver.Sum(qb))
    
    #
    # Add position limits
    #
    for position, limit in POSITION_LIMITS:
        position_cap = solver.Constraint(0, limit)

        for i, player in enumerate(all_players):
            if position == player.position:
                position_cap.SetCoefficient(variables[i], 1)
    
    #
    # Add roster size
    #
    size_cap = solver.Constraint(ROSTER_SIZE, ROSTER_SIZE)
    for variable in variables:
        size_cap.SetCoefficient(variable, 1)
        
    solution = solver.Solve()

    if solution == solver.OPTIMAL:
        roster = Roster()

        with open('Results.csv', 'wb') as csvfile:
            writer = csv.DictWriter(csvfile,delimiter=',',quotechar='"',fieldnames = ["Position","Name","Team","Salary","Projected"])
            writer.writeheader()
        
        with open('Results.csv', 'a') as csvfile:
            writer = csv.writer(csvfile,quotechar='"')
            writer.writerow(["Lineup based on Fanduel FPPG","","","","",])

        for i, player in enumerate(all_players):
            if variables[i].solution_value() == 1:
                roster.add_player(player)
                
                with open('Results.csv', 'a') as csvfile:
                    writer = csv.writer(csvfile,delimiter=',',quotechar='"',quoting=csv.QUOTE_NONNUMERIC)
                    writer.writerow(player.export_csv())
                    
        with open('Results.csv', 'a') as csvfile:
            writer = csv.writer(csvfile,delimiter=',',quotechar='"',quoting=csv.QUOTE_NONNUMERIC)
            writer.writerow(['','','','',roster.projected()])
        
        print "Fanduel FFPG Lineup"
        print "Optimal roster for: $%s\n" % SALARY_CAP
        print roster

    else:
        print "No solution :("

        
if __name__ == "__main__":
    run()
