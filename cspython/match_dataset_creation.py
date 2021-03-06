import sys
from cspython.merging_processing import combine_dfs
sys.setrecursionlimit(15000)
import numpy as np
import pandas as pd
import itertools
#############################################################################################################
# match_dataset_creation.py comes in three parts.
# 1.the creation of columns using the unchanged player data dataset that comes from merging_processing.py. "player_based_column_making(data)"
# 2.the grouping of player data into match data  "apply_nummeric_and_group_as_match(data)"
# 3.the creation of historic columns after grouping the dataset, by match_id. "create_historic_data(data)"


def create_opponent_team_col(data): # creates a column that gives the name of the opponent of the team in that row
    data.loc[:,'player_team_opponent'] = np.nan
    data.loc[(data['team_A_name'] != data['player_team_name']),'player_team_opponent'] = data.loc[:,'team_A_name']
    data.loc[(data['team_B_name'] != data['player_team_name']),'player_team_opponent'] = data.loc[:,'team_B_name']
    return data


def create_fwa_dr_columns(data, col_list):  # first kill , awp kills, who killed who, divided by rounds
    columns = pd.Series(data.columns)
    for a in col_list:
        col = columns[columns.str.contains(a)]
        data[a + '_sum_dr'] = data[col].convert_objects(convert_numeric=True).sum(axis=1) / (
        data['team_A_score'] + data['team_B_score']) * 100
    data.loc[:, data.columns != 'date'] = data.loc[:, data.columns != 'date'].apply(pd.to_numeric, errors='ignore')
    return data


def create_player_columns(data): # creates the columns that represents if who is playing for the team for each match
    names = data.nicknames.unique()
    for a in names:
        data.loc[:, a] = 0
        data.loc[data.loc[:, 'nicknames'] == a, a] = 5  # its 5 so that when you group by team it becomes 1
    return data

def player_based_column_making(data): # these are the functions that are non historic and arent grouped by match_id
    col_list = ['first_kills', 'who_kill_who', 'awp_kills']
    data = create_opponent_team_col(data)
    data = create_fwa_dr_columns(data, col_list)
    data = create_player_columns(data)
    return data

def apply_nummeric_and_group_as_match(data): #make everything numeric and create the grouping necessary for historic functions
    r = data.loc[:, data.columns != 'date'].apply(pd.to_numeric, errors='ignore')
    r['date'] = data.date
    data = r
    data = data.fillna(0)
    data_match = data.groupby(['match_id', 'player_team_name', 'date', 'team_A_name', 'team_B_name', 'series_id', 'map', 'winner_of_match', 'loser_of_match','player_team_opponent']).mean()
    data_match = pd.DataFrame(data_match)
    data_match = data_match.reset_index()
    return data_match

def create_matches_count(data):  # how many matches a team has played
    teams = list(data.player_team_name.unique())
    new_group = pd.DataFrame()
    for a in teams:
        data_team = data.loc[data.loc[:, 'player_team_name'] == a,].sort_values(by=['date', 'series_id','match_num'], ascending=True)
        grouping = data_team.groupby(['player_team_name', 'date', 'series_id','match_num'])['ADR'].count()
        grouping = pd.DataFrame(grouping)
        grouping = grouping.reset_index()
        grouping.loc[:, 'ADR'] = grouping.loc[:, 'ADR'].expanding(min_periods=1, freq=None, center=False, axis=0).sum()
        grouping = grouping.rename(index=str, columns={'ADR': 'matches_played_team'})
        new_group = pd.concat([new_group, grouping])
    data = pd.merge(data, new_group, on=['player_team_name', 'date', 'series_id','match_num'])
    return data


def create_avdamage_his(data):  # column with historic average damage of individual
    teams = list(data.player_team_name.unique())
    new_group = pd.DataFrame()
    for a in teams:
        data_team = data.loc[data.loc[:, 'player_team_name'] == a,].sort_values(by=['date', 'series_id','match_num'], ascending=True)
        grouping = data_team.groupby(['player_team_name', 'date','series_id','match_num'])['ADR'].max()
        grouping = pd.DataFrame(grouping)
        grouping = grouping.reset_index()
        grouping.loc[:, 'ADR'] = grouping.loc[:, 'ADR'].expanding(min_periods=1, freq=None, center=False, axis=0).mean()
        grouping = grouping.rename(index=str, columns={'ADR': 'ADR_hist'})
        new_group = pd.concat([new_group, grouping])
    data = pd.merge(data, new_group, on=['player_team_name', 'date','series_id','match_num'])
    return data


def create_avdamage_map_his(data):  # historic average damage of individual for each map
    teams = list(data.player_team_name.unique())
    maps = list(data.map.unique())
    new_group = pd.DataFrame()
    for a in maps:
        for b in teams:
            data_team = data.loc[(data.loc[:, 'player_team_name'] == b) & (data.loc[:, 'map'] == a),].sort_values(
                by=['date', 'series_id','match_num'], ascending=True)
            grouping = data_team.groupby(['player_team_name', 'date', 'series_id','match_num'])['ADR'].max()
            grouping = pd.DataFrame(grouping)
            grouping = grouping.reset_index()
            grouping.loc[:, 'ADR'] = grouping.loc[:, 'ADR'].expanding(min_periods=1, freq=None, center=False,
                                                                      axis=0).mean()
            grouping = grouping.rename(index=str, columns={'ADR': 'ADR_hist_on_map'})
            new_group = pd.concat([new_group, grouping])

    data = pd.merge(data, new_group, on=['player_team_name', 'date', 'series_id', 'match_num'])

    return data

def create_fwadr_his(data, col_list): # historic first/awp/who kills divided by rounds
    teams = list(data.player_team_name.unique())
    for b in col_list:
        new_group = pd.DataFrame()
        for a in teams:
            data_team = data.loc[data.loc[:,'player_team_name'] == a, ].sort_values(by=['date','series_id','match_num'],ascending=True)
            grouping = data_team.groupby(['player_team_name', 'date', 'series_id', 'match_num'])[b+'_sum_dr'].max()
            grouping = pd.DataFrame(grouping)
            grouping = grouping.reset_index()
            grouping.loc[:,b +'_sum_dr'] = grouping.loc[:,b +'_sum_dr'].expanding(min_periods=1, freq=None, center=False, axis=0).mean()
            grouping = grouping.rename(index=str, columns={b +'_sum_dr': b + '_sum_dr_hist'})
            new_group = pd.concat([new_group, grouping])
        data = pd.merge(data, new_group, on = ['player_team_name', 'date', 'series_id','match_num'])
    return data


def create_faw_map_his(data, col_list): # historic first/awp/who kills divided by rounds for each map
    teams = list(data.player_team_name.unique())
    maps = list(data.map.unique())
    for b in col_list:
        new_group = pd.DataFrame()
        for i in maps:
            for a in teams:
                data_team = data.loc[(data.loc[:, 'player_team_name'] == a) & (data.loc[:, 'map'] == i),].sort_values(
                    by=['date', 'series_id','match_num'], ascending=True)
                grouping = data_team.groupby(['player_team_name', 'date', 'series_id','match_num'])[b + '_sum_dr'].max()
                grouping = pd.DataFrame(grouping)
                grouping = grouping.reset_index()
                grouping.loc[:, b + '_sum_dr'] = grouping.loc[:, b + '_sum_dr'].expanding(min_periods=1, freq=None,
                                                                                          center=False, axis=0).mean()
                grouping = grouping.rename(index=str, columns={b + '_sum_dr': b + '_sum_dr_hist_on_map'})
                new_group = pd.concat([new_group, grouping])

        data = pd.merge(data, new_group, on=['player_team_name', 'date', 'series_id', 'match_num'])
    return data

def create_historic_data(data): # all the functions  that are creating match based historic data
    col_list = ['first_kills', 'who_kill_who', 'awp_kills']
    data = create_fwadr_his(data, col_list)
    data = create_matches_count(data)
    data = create_avdamage_his(data)
    data = create_avdamage_map_his(data)
    data = create_faw_map_his(data, col_list)

    return data
    
def count_map_win_loss_total(df): #this function assumes the df contains only rows from one team
    team_name = df.player_team_name.iloc[0]
    maps = df.map.unique()
    
    for map_name in maps:
        df[map_name + "_win_his"] = np.nan
        df[map_name + "_loss_his"] = np.nan
        df[map_name + "_total_played"] = np.nan
        
    grouped = df.groupby('map')
    for map_name, map_df in grouped:
        played = pd.Series(range(1,len(map_df)+1), index=map_df.index)
        won = (map_df.winner_of_match == team_name).expanding(1).sum()
        lost = played - won
        
        df.loc[map_df.index, map_name + '_total_played'] = played
        df.loc[map_df.index, map_name + '_win_his'] = won
        df.loc[map_df.index, map_name + '_loss_his'] = lost
        
        df.loc[:, map_name + '_total_played'].fillna(method='ffill', inplace=True)
        df.loc[:, map_name + '_win_his'].fillna(method='ffill', inplace=True)
        df.loc[:, map_name + '_loss_his'].fillna(method='ffill', inplace=True)
        
        df.loc[:, map_name + '_total_played'].fillna(0, inplace=True)
        df.loc[:, map_name + '_win_his'].fillna(0, inplace=True)
        df.loc[:, map_name + '_loss_his'].fillna(0, inplace=True)
        
    return df


def create_map_win_loss_and_per_his_columns(data):  # team total win and loses on map with total times played on map !4!
    data.sort_values(['date', 'series_id','match_num'], inplace=True)
    data.index = range(len(data))
    original_col_order = data.columns.tolist()
    data = data.groupby('player_team_name').apply(count_map_win_loss_total)
    new_cols = data.columns[~data.columns.isin(original_col_order)].tolist()
    data = data.loc[:, original_col_order + new_cols]
    for map_name in data.map.unique():
        data.loc[:, map_name + '_win_perc_map'] = data.loc[:, map_name + '_win_his']/data.loc[:, map_name + '_total_played']
    return data
    
def create_rounds_won_rounds_loss_columns(data):
    team_A_rounds = data.loc[data.player_team_name == data.team_A_name, 'team_A_score']
    team_B_rounds = data.loc[data.player_team_name == data.team_B_name, 'team_B_score']
    rounds_won = pd.concat([team_A_rounds, team_B_rounds])
    data.loc[:, 'rounds_won'] = rounds_won
    
    team_A_rounds = data.loc[data.player_team_name == data.team_B_name, 'team_A_score']
    team_B_rounds = data.loc[data.player_team_name == data.team_A_name, 'team_B_score']
    rounds_lost = pd.concat([team_A_rounds, team_B_rounds])
    data.loc[:, 'rounds_lost'] = rounds_lost
    
    return data

#running total of rounds won/lost vs opponent

def count_rounds_won_vs_opponent(df): #parsing a df of 1 team
    grouped = df.groupby('player_team_opponent')
    for opponent, opponent_df in grouped:
        won_his = opponent_df.loc[:, 'rounds_won'].expanding(1).sum()
        loss_his = opponent_df.loc[:,'rounds_lost'].expanding(1).sum()
        
        df.loc[opponent_df.index, 'rounds_won_vs_'+opponent] = won_his
        df.loc[opponent_df.index, 'rounds_loss_vs_'+opponent] = loss_his
        
        df.loc[:, 'rounds_won_vs_'+opponent].fillna(method='ffill', inplace=True)
        df.loc[:, 'rounds_loss_vs_'+opponent].fillna(method='ffill', inplace=True)
        
        df.loc[:, 'rounds_won_vs_'+opponent].fillna(0, inplace=True)
        df.loc[:, 'rounds_loss_vs_'+opponent].fillna(0, inplace=True)
    return df


def create_rounds_won_and_lost_vs_team_his(data): #applied to entire dataset
    data.sort_values(['date', 'series_id', 'match_num'], inplace = True)
    data = data.groupby('player_team_name').apply(count_rounds_won_vs_opponent)
    return data


def count_rounds_won_vs_opponent_on_map(df): # parsing a df of 1 team
    opponent = df.player_team_opponent.values[0]
    map_name = df.map.values[0]

    won_his = df.loc[:, 'rounds_won'].expanding(1).sum()
    loss_his = df.loc[:,'rounds_lost'].expanding(1).sum()
        
    df.loc[:, 'rounds_won_vs_'+opponent+'_on_'+map_name] = won_his
    df.loc[:, 'rounds_loss_vs_'+opponent+'_on_'+map_name] = loss_his

    return df


def create_rounds_won_and_lost_vs_team_by_map_his(data):
    data.sort_values(['date', 'series_id', 'match_num'], inplace = True)
    data = data.groupby(['player_team_name', 'player_team_opponent', 'map']).apply(count_rounds_won_vs_opponent_on_map)
    
    for team, opponent, map_name in itertools.product(data.player_team_name.unique(), data.player_team_opponent.unique(), data.map.unique()):
        if 'rounds_won_vs_'+opponent+'_on_'+map_name not in data.columns:
            data.loc[:,'rounds_won_vs_'+opponent+'_on_'+map_name] = 0
            data.loc[:,'rounds_loss_vs_'+opponent+'_on_'+map_name] = 0
            continue
        col = data.loc[data.player_team_name == team, 'rounds_won_vs_'+opponent+'_on_'+map_name].fillna(method='ffill')
        data.loc[data.player_team_name == team, 'rounds_won_vs_'+opponent+'_on_'+map_name] = col
        col = data.loc[data.player_team_name == team, 'rounds_loss_vs_'+opponent+'_on_'+map_name].fillna(method='ffill')
        data.loc[data.player_team_name == team, 'rounds_loss_vs_'+opponent+'_on_'+map_name] = col
        col = data.loc[data.player_team_name == team, 'rounds_won_vs_'+opponent+'_on_'+map_name].fillna(0)
        data.loc[data.player_team_name == team, 'rounds_won_vs_'+opponent+'_on_'+map_name] = col
        col = data.loc[data.player_team_name == team, 'rounds_loss_vs_'+opponent+'_on_'+map_name].fillna(0)
        data.loc[data.player_team_name == team, 'rounds_loss_vs_'+opponent+'_on_'+map_name] = col
    return data
def create_round_his_cols(data):
    original_col_order = data.columns.tolist()
    data = create_rounds_won_rounds_loss_columns(data)
    data = create_rounds_won_and_lost_vs_team_his(data)
    data = create_rounds_won_and_lost_vs_team_by_map_his(data)
    new_cols = data.columns[~data.columns.isin(original_col_order)].tolist()
    data = data.loc[:, original_col_order + new_cols]
    return data
    
    
def match_dataset_creation(data):  #creates player based columns, then groups to allow for historic match based columns
    data = player_based_column_making(data)
    data = apply_nummeric_and_group_as_match(data)
    return data
    
def aggregate_data_over_time(data): #adds aggregate columns
    data = create_historic_data(data)
    data = create_map_win_loss_and_per_his_columns(data)
    data = create_round_his_cols(data)
    return data
    
    
if __name__ == '__main__':
    #data = combine_dfs(overview, big_data)
    #data = match_dataset_creation(data)
    #data = aggregate_data_over_time(data)

    pass