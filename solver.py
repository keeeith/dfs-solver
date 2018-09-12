# Fanduel Solver
# Based on:
# https://github.com/swanson/degenerate
# https://github.com/mrnitrate/Draftkings-Optimal-Lineup-Generator

from ortools.linear_solver import pywraplp
import csv
import itertools as IT

PROJECTION_COUNT = int

SALARY_CAP = 60000

POSITION_LIMITS = [
    ['QB', 1, 1],
    ['RB', 2, 3],
    ['WR', 3, 4],
    ['TE', 1, 2],
    ['D', 1, 1],
]

ROSTER_SIZE = 9
TEAM_MAX = 4

class Player:

    def __init__(self, opts):
        self.id = opts['Id']
        self.position = opts['Position'].upper()
        self.name = opts['Name']
        self.salary = int(opts['Salary'])
        self.index = 0
        self.projected = []
        self.projection = []

        column_names = ["FPPG","New projection","Another projection","Yet another projection"]

        global PROJECTION_COUNT
        PROJECTION_COUNT = len(column_names)

        for column in column_names:
            self.projection.append(column)
            try:
                self.projected.append( float(opts[column]))
            except:
                self.projected.append( float(0))

        self.team = opts['Team']
        self.opponent = opts['Opponent']
        self.lock = int(opts['Lock']) > 0
        self.ban = int(opts['Lock']) < 0

    def set_index(self,index):
        self.index = index

    def __repr__(self):
        return "{0},{1},{2},${3},{4}".format(self.position, \
                                    self.name, \
                                    self.team, \
                                    self.salary, \
                                    self.projected[self.index],
                                    "LOCK" if self.lock else "")

    def export_csv(self):
        csv_obj = [self.position,self.name,self.team,self.salary,self.projected[self.index]]
        return csv_obj

class Roster:
    POSITION_ORDER = {
        "QB": 0,
        "WR": 1,
        "RB": 2,
        "TE": 3,
        "D": 4,
    }

    def __init__(self):
        self.players = []
        self.index = 0

    def add_player(self, player, index):
        self.players.append(player)
        self.index = index

    def spent(self):
        return sum(map(lambda x: x.salary, self.players))

    def projected(self,index):
        return sum(map(lambda x: x.projected[index], self.players))

    def position_order(self, player):
        return self.POSITION_ORDER[player.position]
    
    def sorted_players(self):
        sortedp = sorted(self.players, key=self.position_order)
        rbs = list(filter(lambda x: x.position=='RB', self.players))
        wrs = list(filter(lambda x: x.position=='WR', self.players))
        
        if (len(rbs)>2):
            sortedp.insert(7,sortedp.pop(3))
        elif (len(wrs)>3):
            sortedp.insert(7,sortedp.pop(6))
        
        return sortedp

    def __repr__(self):
        s = '\n'.join(str(x) for x in self.sorted_players())
        s += "\nProjected Score: %s" % self.projected(self.index)
        s += "\nCost: $%s\n" % self.spent()
        return s    
    
    

def run(all_players):
    with open('Results.csv', 'w') as csvfile:
        writer = csv.DictWriter(csvfile,delimiter=',',quotechar='"',fieldnames = ["Position","Name","Team","Salary","Projected"])
        writer.writeheader()

    for x in range(0, PROJECTION_COUNT):
        solver = pywraplp.Solver('FD', pywraplp.Solver.CBC_MIXED_INTEGER_PROGRAMMING)
        variables = []

        for player in all_players:
            if player.lock:
                variables.append(solver.IntVar(1, 1, player.id))
            elif player.ban:
                variables.append(solver.IntVar(0, 0, player.id))
            else:
                player.set_index(x)
                variables.append(solver.IntVar(0, 1, player.id))

        objective = solver.Objective()
        objective.SetMaximization()

        #
        # Add projected points for each player
        #
        for i, player in enumerate(all_players):
            objective.SetCoefficient(variables[i], player.projected[x])

        #
        # Add salary cap and salary for each player

        salary_cap = solver.Constraint(0, SALARY_CAP)
        for i, player in enumerate(all_players):
            salary_cap.SetCoefficient(variables[i], player.salary)

        #
        # Add minimum number of teams players must be drafted from
        # Fanduel requires that you have players from at least 3 different teams
        #
        team_names = set([o.team for o in all_players])
        teams = []
        for team in team_names:
            teams.append(solver.IntVar(0, 1, team))

        solver.Add(solver.Sum(teams)>=3)

        for i, team in enumerate(team_names):
            ids, players_by_team = zip(*filter(lambda x: x[0].team in team, zip(all_players, variables)))
            solver.Add(teams[i]<=solver.Sum(players_by_team))

        #
        # Add max number of offense-players per team constraint (Fanduel <= 4)
        # Fanduel requires that you don't have any more than 4 players from the same team
        #
        for team in list(team_names):
            ids, players_by_team = zip(*filter(lambda x: x[0].team in team, zip(all_players, variables)))
            solver.Add(solver.Sum(players_by_team)<=4)

        #
        # Make sure the defense chosen is NOT any of the offense players team OPPONENT for the week.
        # This way high scoring defenses are not also shutting down your offense players.
        # It does not check if the defense is not the same team as the offense's players.
        #
        o_players = filter(lambda x: x.position in ['QB','WR','RB','TE'], all_players)
        opps_team_names= set([o.opponent for o in o_players])
        teams_obj = filter(lambda x: x.position == 'D' , all_players)
        teams = set([o.team for o in teams_obj])
        for opps_team in team_names:
            if opps_team in teams :
                ids, players_by_opps_team = zip(*filter(lambda x: x[0].position in ['QB','WR','RB','TE'] and x[0].opponent in opps_team, zip(all_players, variables)))
                idxs, defense = zip(*filter(lambda x: x[0].position == 'D' and x[0].team in opps_team, zip(all_players, variables)))
                for player in players_by_opps_team:
                    solver.Add(player<=1-defense[0])
                    
        #
        # Add QB stacking (at least 1 wr or te on same team as QB) constraint
        #
        offense_team_names = set([o.team for o in o_players])
        for o_team in offense_team_names:
            ids, players_by_team = zip(*filter(lambda x: x[0].position in ['WR','TE'] and x[0].team == o_team, zip(all_players, variables)))
            idxs, qb = zip(*filter(lambda x: x[0].position == 'QB' and x[0].team == o_team, zip(all_players, variables)))
            solver.Add(solver.Sum(players_by_team)>=solver.Sum(qb))

        #
        # Add position limits
        #
        for position, min_limit, max_limit in POSITION_LIMITS:
            position_cap = solver.Constraint(min_limit, max_limit)

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
            projection_title = player.projection[x]

            with open('Results.csv', 'a') as csvfile:
                writer = csv.writer(csvfile,quotechar='"')
                writer.writerow([projection_title,"","","","",])

            for i, player in enumerate(all_players):
                if variables[i].solution_value() == 1:

                    roster.add_player(player,x)

                    with open('Results.csv', 'a') as csvfile:
                        writer = csv.writer(csvfile,delimiter=',',quotechar='"',quoting=csv.QUOTE_NONNUMERIC)
                        writer.writerow(player.export_csv())

            with open('Results.csv', 'a') as csvfile:
                writer = csv.writer(csvfile,delimiter=',',quotechar='"',quoting=csv.QUOTE_NONNUMERIC)
                writer.writerow(['','','','',roster.projected(x)])
            
            print(projection_title+" Lineup:")
            print(roster)

        else:
            print("No solution :(")


def load():
    all_players = []
    filenames = ['Player List.csv', 'Projections.csv']
    handles = [open(filename, 'r') for filename in filenames]
    readers = [csv.DictReader(f, skipinitialspace=True) for f in handles]


    for rows in IT.zip_longest(*readers, fillvalue=['']*2):
        combined_row = {}
        for row in rows:
            combined_row.update(row)
        all_players.append(Player(combined_row))

    for f in handles:
        f.close()

    return all_players


if __name__ == "__main__":
    all_players = load()
    run(all_players)