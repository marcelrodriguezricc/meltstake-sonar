function sonar = parse881a(depname,varargin)
%
% Original by Kaelan Weiss, modified by Marcel Rodriguez-Riccelli
%
% Function to parse data in a Meltstake sonar881a deployment folder. The
% function relies on the files "RunData.csv" (output from binary_convert),
% "RunIndex.csv", and "configuration.json". If working outside of the
% normal Meltstake directory structure, a data folder containing the above
% files can be directly specified.
%
% sonar = parse881a(depname)
% sonar = parse881a(depname,t1,t2)
% sonar = parse881a(depname,__,'data_folder',data_folder)
%
% Input
%   depname: path to the folder containing the subfolder (usually named
%       with a time stamp) which holds the csv files
%   t1: (optional) start of time window to parse
%   t2: (optional) end of time window to parse
%   data_folder: (name-value pair) instead of searching for a data
%       directory in depname/sonar881a/ which holds the csv files, the
%       script looks directly in data_folder (useful outside of meltstake
%       file tree) 
%
% Output
%   sonar: structure containing timestamps, angle, range, and amplitudes 
%       for each of two scans completed per timestamp
%

% ----- Parse secondary function arguments -----

% Function handle - returns true if input is a character array or string
chk_data_dir = @(x) ischar(x) || isstring(x);

% Create input parser object
p = inputParser;

% Add optional start and end time arguments to parser
addOptional(p,'t1',datetime(0,1,1),@isdatetime);
addOptional(p,'t2',datetime('now'),@isdatetime);

% Add data directory argument to parser, uses function handle to ensure it is an array or string
addParameter(p,'data_folder',char(1),chk_data_dir);

% Parse secondary arguments and assign to local variables
parse(p,varargin{:});
t1 = p.Results.t1; 
t2 = p.Results.t2;

% Assign primary argument to local variable
data_folder = p.Results.data_folder;

% ----- Get files from directory -----

% Set directory from primary input and append sub-directory "sonar881a/"
d = dir(fullfile(depname,'sonar881a'));

% If a data folder was not specified as a secondary argument when the function was called...
if data_folder == char(1)

    % Reset to an empty string
    data_folder = '';

    % Loop trough directory files
    for i = 1:length(d)

        % Check that the input directory is actually a directory, contains
        % RunIndex.csv, RunData.csv, and configuration.json, and set that
        % as the data folder
        if ~(d(i).name(1)=='.') && exist(fullfile(depname,'sonar881a',d(i).name),'dir') ...
                && exist(fullfile(depname,'sonar881a',d(i).name,'RunIndex.csv'),'file') ...
                && exist(fullfile(depname,'sonar881a',d(i).name,'RunData.csv'),'file') ...
                && exist(fullfile(depname,'sonar881a',d(i).name,'configuration.json'),'file')
            data_folder = d(i).name;
            break
        end
    end

    % If the data folder does not pass the check, return error
    if isempty(data_folder)
        error('unable to find RunIndex.csv, RunData.csv, and configuration.json in %s',data_folder)
    
    % Or else set the data_path automatically
    else
        data_path = fullfile(depname,'sonar881a',data_folder);
    end

% Else if the data folder was specified... 
else
    
    % And if the specified data folder is a directory and contains
    % RunIndex.csv, RunData.csv, and configuration.json, set that as the
    % data folder
    if exist(data_folder,'dir') ...
                && exist(fullfile(data_folder,'RunIndex.csv'),'file') ...
                && exist(fullfile(data_folder,'RunData.csv'),'file') ...
                && exist(fullfile(data_folder,'configuration.json'),'file')
        data_path = data_folder;
    else
        error('unable to find RunIndex.csv, RunData.csv, and configuration.json in %s',data_folder)
    end
end

% Set local variables for the paths to RunData.csv, RunIndex.csv, and
% configuration.json
dat_file = fullfile(data_path,'RunData.csv');
idx_file = fullfile(data_path,'RunIndex.csv');
cfg_file = fullfile(data_path,'configuration.json');

% ----- Count RunData.csv headers-----

% Open RunData.csv
fid = fopen(dat_file,'r');

% Get the first line (headers)
dat_hdrs = strsplit(fgetl(fid),',');

% Close the file
fclose(fid);

% Count the number of headers
nh = length(dat_hdrs);

% ----- Open files -----

% Convert RunData.csv into a table
dat_tbl = readtable(dat_file);

% Convert RunIndex.csv into a table (first row is not column headers)
idx_tbl = readtable(idx_file,'readvariablenames',false);

% Convert configuration.json into Matlab struct
cfg = readstruct(cfg_file);

% ----- Get parameters from config -----

% Scan range from configuration
max_rng = cfg.scan.range;

% Get number of sweeps in a scan from configuration
num_sweeps = cfg.scan.num_sweeps;

% ----- Set time range logic mask filter -----

% Extract times from first column of table
time = idx_tbl{:,1};
% disp(time)
% disp(t1)
% 
% % Create logic mask, true for times between t1 and t2 (if specified)
% idx_time = time>=t1 & time<=t2;
% 
% % Apply the logic mask to remove all times not in range
% time = time(idx_time);


% ----- Number rows based on scan number, apply time range filter -----

% Get number of RunIndex rows
ns = size(idx_tbl,1);

% Get number of RunData rows
nr = size(dat_tbl,1);

% Initialize number of scans variable with NaN values
scan_num = nan(ns,1);

% For each row in RunIndex...
for i = 1:ns
    % Extract filename for each scan and to pertinent number
    scan_num(i) = str2double(idx_tbl{i,3}{1}(10:end-4));
end

% Apply time filter mask
% scan_num = scan_num(idx_time);


% ----- Get number of scans, and range sample, angle, and direction data
% for each scan -----

% Get number of scans
% ns = sum(idx_time);

% Get the number of range samples stored per ping (row)
nb = size(dat_tbl,2)-nh+1;

% Initialize a variable for each row in RunData
row_scan = nan(nr,1);

% For each row in RunData...
for i = 1:nr

    % Assign it the appropriate scan number
    row_scan(i) = str2double(dat_tbl{i,1}{1}(10:end-4));
end

% Find the column that corresponds to the 'scan_index' header
idx_col = strcmp(dat_hdrs,'scan_index');
a_col = strcmp(dat_hdrs,'headposition');
dir_col = strcmp(dat_hdrs,'stepdirection');

% Ascertain the number of pings per scan by looking the number of unique
% scan indices
num_pings = length(unique(dat_tbl{:,idx_col}));

% Get the number of scans by dividing the RunData table by the number of
% pings per scan, with a floor to exclude incomplete scans
num_scans = floor(height(dat_tbl) / num_pings);

% Initialize a new cell array to hold each scan table
scan_tbls = cell(num_scans, 1);

% For each scan
for k = 1:num_scans
    
    % Indentify first row of the scan
    r0 = (k-1) * num_pings + 1;

    % Identify last row of the scan
    r1 = k * num_pings;

    % Break pertinent rows of dat table into a sub-table and store in scan_tbls cell array
    scan_tbls{k} = dat_tbl(r0:r1, :);
end

cw_angles  = cell(numel(scan_tbls), 1);
ccw_angles = cell(numel(scan_tbls), 1);
cw_dirs    = cell(numel(scan_tbls), 1);
ccw_dirs   = cell(numel(scan_tbls), 1);
ccw_dists = cell(numel(scan_tbls), 1);
cw_dists  = cell(numel(scan_tbls), 1);

for k = 1:numel(scan_tbls)
    scan_tbl = scan_tbls{k};

    dists  = scan_tbl{:,nh:end};
    angles = scan_tbl{:, a_col};
    dirs   = string(scan_tbl{:, dir_col});

    is_cw  = (lower(dirs) == "cw");
    is_ccw = (lower(dirs) == "ccw");

    cw_angles{k}  = angles(is_cw);
    ccw_angles{k} = angles(is_ccw);

    cw_dirs{k}    = dirs(is_cw);
    ccw_dirs{k}   = dirs(is_ccw);

    cw_dists{k}    = dists(is_cw, :);
    ccw_dists{k}   = dists(is_ccw, :);

    [cw_angles{k}, ord] = sort(cw_angles{k}, 'ascend');
    cw_dirs{k}  = cw_dirs{k}(ord);
    cw_dists{k} = cw_dists{k}(ord, :);

    [ccw_angles{k}, ord] = sort(ccw_angles{k}, 'ascend');
    ccw_dirs{k}  = ccw_dirs{k}(ord);
    ccw_dists{k} = ccw_dists{k}(ord, :);
    
end

sonar = struct();
sonar.range = max_rng * linspace(0,1,nb)';

sonar.scans = repmat(struct( ...
    'cw_angles', [], 'cw_dirs', [], 'cw_dists', [], ...
    'ccw_angles', [], 'ccw_dirs', [], 'ccw_dists', []), numel(scan_tbls), 1);

for k = 1:numel(scan_tbls)
    sonar.scans(k).cw_angles = cw_angles{k};
    sonar.scans(k).cw_dirs   = cw_dirs{k};
    sonar.scans(k).cw_dists  = cw_dists{k};  

    sonar.scans(k).ccw_angles = ccw_angles{k};
    sonar.scans(k).ccw_dirs   = ccw_dirs{k};
    sonar.scans(k).ccw_dists  = ccw_dists{k};
end