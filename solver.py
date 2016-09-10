# Fanduel Solver
# Based on:
# https://github.com/swanson/degenerate
# https://github.com/mrnitrate/Draftkings-Optimal-Lineup-Generator

from ortools.linear_solver import pywraplp
import csv
import itertools as IT

# Change this for the number of projections you need to run
PROJECTION_COUNT = 21

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

class Player:

    def __init__(self, opts):
        self.id = opts['Id']
        self.position = opts['Position'].upper()
        self.name = opts['Name']
        self.salary = int(opts['Salary'])
        self.index = 0
        #Sometimes projections have bad or missing projection for players, so we need to check
        self.projected = []
        self.projection = []
        #1
        try:
            self.projected.append(float(opts['Fanduel']))
            self.projection.append('Fanduel')
        except:
            self.projected.append( float(0))
        #2
        try:
            self.projected.append( float(opts['Owned 50/50']))
            self.projection.append('Owned 50/50')
        except:
            self.projected.append( float(0))
        #3
        try:
            self.projected.append( float(opts['Owned GPP']))
            self.projection.append('Owned GPP')
        except:
            self.projected.append( float(0))
        #4
        try:
            self.projected.append(float(opts['Owned Combined']))
            self.projection.append('Owned Combined')
        except:
            self.projected.append( float(0))
        #5
        try:
            self.projected.append( float(opts['Formula 7']))
            self.projection.append('Formula 7')
        except:
            self.projected.append( float(0))
        #6
        try:
            self.projected.append( float(opts['Formula 8']))
            self.projection.append('Formula 8')
        except:
            self.projected.append( float(0))
        #7
        try:
            self.projected.append(float(opts['Formula 5']))
            self.projection.append('Formula 5')
        except:
            self.projected.append( float(0))
        #8
        try:
            self.projected.append( float(opts['Formula 6']))
            self.projection.append('Formula 6')
        except:
            self.projected.append( float(0))
        #9
        try:
            self.projected.append( float(opts['Formula 9']))
            self.projection.append('Formula 9')
        except:
            self.projected.append( float(0))
        #10
        try:
            self.projected.append(float(opts['FFA Points']))
            self.projection.append('FFA Points')
        except:
            self.projected.append( float(0))
        #11
        try:
            self.projected.append( float(opts['FFA Ceiling']))
            self.projection.append('FFA Ceiling')
        except:
            self.projected.append( float(0))
        #12
        try:
            self.projected.append( float(opts['FFA Floor']))
            self.projection.append('FFA Floor')
        except:
            self.projected.append( float(0))
        #13
        try:
            self.projected.append( float(opts['FFA Points/Ceiling Avg']))
            self.projection.append('FFA Points/Ceiling Avg')
        except:
            self.projected.append( float(0))
        #14
        try:
            self.projected.append( float(opts['FFA Points/Floor Avg']))
            self.projection.append('FFA Points/Floor Avg')
        except:
            self.projected.append( float(0))
        #15
        try:
            self.projected.append( float(opts['FFA Ceiling/Floor Avg']))
            self.projection.append('FFA Ceiling/Floor Avg')
        except:
            self.projected.append( float(0))                  
        #16
        try:
            self.projected.append( float(opts['FantasyPros']))
            self.projection.append('FantasyPros')
        except:
            self.projected.append( float(0))                  
        #17
        try:
            self.projected.append( float(opts['FantasyLabs']))
            self.projection.append('FantasyLabs')
        except:
            self.projected.append( float(0))              
        #18
        try:
            self.projected.append( float(opts['FantasyLabs3']))
            self.projection.append('FantasyLabs3')
        except:
            self.projected.append( float(0))                   
        #19
        try:
            self.projected.append( float(opts['FantasyLabs4']))
            self.projection.append('FantasyLabs4')
        except:
            self.projected.append( float(0))                   
        #20
        try:
            self.projected.append( float(opts['Rotogrinders']))
            self.projection.append('Rotogrinders')
        except:
            self.projected.append( float(0))
        #21
        try:
            self.projected.append( float(opts['Counting']))
            self.projection.append('Counting')
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
        "K": 4,
        "D": 5,
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
        return sorted(self.players, key=self.position_order)

    def __repr__(self):
        s = '\n'.join(str(x) for x in self.sorted_players())
        s += "\nProjected Score: %s" % self.projected(self.index)
        s += "\tCost: $%s" % self.spent()
        s += "\n"
        return s

def write_bulk_import_csv(rosters):
    with open('test.csv', 'wb') as csvfile:
        writer = csv.writer(csvfile,delimiter=',',quotechar='"',quoting=csv.QUOTE_NONNUMERIC)
        for roster in rosters:
            writer.writerow([x.name for x in roster.sorted_players()])

def run(all_players):
    with open('Results.csv', 'wb') as csvfile:
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
            ids, players_by_team = zip(*filter(lambda (x,_): x.team in team, zip(all_players, variables)))
            solver.Add(teams[i]<=solver.Sum(players_by_team))

        #
        # Add max number of offense-players per team constraint (Fanduel <= 4)
        # Fanduel requires that you don't have any more than 4 players from the same team
        #
        #     for team in list(team_names):
        #         team_players = filter(lambda x: x.team in team, all_players)
        #         ids, players_by_game = zip(*filter(lambda (x,_): x.team in team and x.position in ['WR','TE','RB','QB'], zip(all_players, variables)))
        #         solver.Add(solver.Sum(players_by_game)<=4)
        for team in list(team_names):
            ids, players_by_team = zip(*filter(lambda (x,_): x.team in team, zip(all_players, variables)))
            solver.Add(solver.Sum(players_by_team)<=4)

        #
        # Make sure the defense chosen is NOT any of the offense players team OPPONENT for the week.
        # This way high scoring defenses are not also shutting down your offense players.
        # It does not check if the defense is not the same team as the offense's players.
        #
        #     o_players = filter(lambda x: x.position in ['QB','WR','RB','TE'], all_players)
        #     opps_team_names= set([o.opponent for o in o_players])
        #     teams_obj = filter(lambda x: x.position == 'D' , all_players)
        #     teams = set([o.team for o in teams_obj])
        #     for opps_team in team_names:
        #         if opps_team in teams :
        #             ids, players_by_opps_team = zip(*filter(lambda (x,_): x.position in ['QB','WR','RB','TE'] and x.opponent in opps_team, zip(all_players, variables)))
        #             idxs, defense = zip(*filter(lambda (x,_): x.position == 'D' and x.team in opps_team, zip(all_players, variables)))
        #             solver.Add(solver.Sum(1-x for x in players_by_opps_team)+solver.Sum(1-x for x in defense)>=1)
        #
        o_players = filter(lambda x: x.position in ['QB','WR','RB','TE','K'], all_players)
        opps_team_names= set([o.opponent for o in o_players])
        teams_obj = filter(lambda x: x.position == 'D' , all_players)
        teams = set([o.team for o in teams_obj])
        for opps_team in team_names:
            if opps_team in teams :
                ids, players_by_opps_team = zip(*filter(lambda (x,_): x.position in ['QB','WR','RB','TE'] and x.opponent in opps_team, zip(all_players, variables)))
                idxs, defense = zip(*filter(lambda (x,_): x.position == 'D' and x.team in opps_team, zip(all_players, variables)))
                for player in players_by_opps_team:
                    solver.Add(player<=1-defense[0])

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
            projection_title = player.projection[x]
            #with open('Results.csv', 'a') as csvfile:
            #  writer = csv.DictWriter(csvfile,delimiter=',',quotechar='"',fieldnames = ["Position","Name","Team","Salary","Projected"])
            #  writer.writeheader()

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

            print projection_title+" Lineup:"
            #print "Optimal roster for: $%s\n" % SALARY_CAP
            print roster

        else:
            print "No solution :("


def load():
    all_players = []
    filenames = ['FanDuel-NFL-2016-09-11-16073-players-list.csv', 'Projections.csv']
    handles = [open(filename, 'rb') for filename in filenames]
    readers = [csv.DictReader(f, skipinitialspace=True) for f in handles]


    for rows in IT.izip_longest(*readers, fillvalue=['']*2):
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