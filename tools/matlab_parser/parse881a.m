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

% Create logic mask, true for times between t1 and t2 (if specified)
idx_time = time>=t1 & time<=t2;

% Apply the logic mask to remove all times not in range
time = time(idx_time);

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
scan_num = scan_num(idx_time);


% ----- Get number of scans, and range sample, angle, and direction data
% for each scan -----

% Get number of scans
ns = sum(idx_time);

% Initialize a variable for each row in RunData
row_scan = nan(nr,1);

% For each row in RunData...
for i = 1:nr

    % Assign it the appropriate scan number
    row_scan(i) = str2double(dat_tbl{i,1}{1}(10:end-4));
end

% Find which column contains the head angle data
a_col = strcmp(dat_hdrs,'headposition');

% Find which column contains the step direction data
dir_col = strcmp(dat_hdrs,'stepdirection');

% Get the number of range samples stored per ping (row)
nb = size(dat_tbl,2)-nh+1;

% Compute the number of angles per scan
na = 2*length(unique(dat_tbl{:,a_col}));

% Initialize variables to hold scan and angle data
scan_data = nan(ns,na,nb);
angle_data = nan(ns,na);


% Get the range samples, angle, and direction data for each row (scan)
all_scans = dat_tbl{:,nh:end};
all_angles = dat_tbl{:,a_col};
all_dirs = dat_tbl{:,dir_col};

% ----- Remove final scan if incomplete -----

% For each scan...
for i = 1:ns
    
    % Select row
    idx = row_scan==scan_num(i);

    % Get the range data and angles
    scani = all_scans(idx,:);
    anglei = all_angles(idx, :);

    % Get the initial angle
    a0 = anglei(1);

    % Find where initial angle occurs
    fidx = find(anglei==a0);

    % Check that initial angle occurs a number of times coinciding with the
    % number of sweeps in a scan from configuration, if not, drop the scan
    % as incomplete
    if i==ns && length(fidx)~=num_sweeps
        idx_final = i-1;
        scan_data = scan_data(1:idx_final,:,:);
        angle_data = angle_data(1:idx_final,:);
        time = time(1:idx_final);
        break
    end

    % Get direction data for each row
    diri = string(all_dirs(idx));

    % Split the data into clockwise and counter-clockwise
    is_cw  = diri == "cw";
    is_ccw = diri == "ccw";
    scani_cw   = scani(is_cw, :);
    anglei_cw  = anglei(is_cw);
    scani_ccw  = scani(is_ccw, :);
    anglei_ccw = anglei(is_ccw);
    
    % Flip the clockwise portion so angles are ordered
    scani_cw  = flipud(scani_cw);
    anglei_cw = flipud(anglei_cw);

    angle_data = [anglei_ccw; anglei_cw];
    scan_data = [scani_ccw; scani_cw];

end

sonar = struct( ...
    'time',  time, ...
    'angle', angle_data, ...
    'range', max_rng * linspace(0,1,nb)',...
    'scan', scan_data ...
);