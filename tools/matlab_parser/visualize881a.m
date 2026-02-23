function sonar = visualize881a(inputArg)

    if isstruct(inputArg)
        sonar = inputArg;

    else
        S = load(inputArg);
        sonar = S.sonar;
    end

    % Get first scan time
    t0 = sonar.scans(1).time;
    t0_str = datestr(t0, 'yyyy-mm-dd_HHMMSS');
    
    % Script directory
    scriptFullPath = mfilename('fullpath');
    scriptFolder   = fileparts(scriptFullPath);
    
    % images/<timestamp> folder
    imageFolder = fullfile(scriptFolder, 'images', t0_str);
    
    if ~exist(imageFolder, 'dir')
        mkdir(imageFolder);
    end

    % For each scan...
    for k = 1:numel(sonar.scans)
    
    % Get field data
    ang = sonar.scans(k).cw_angles;
    A   = sonar.scans(k).cw_dists;
    B   = sonar.scans(k).ccw_dists;
    
    % Average CW and CCW scans
    P = (A + B) / 2;

    % Get ranges from range field
    r = sonar.range(:)'; 
    
    % Convert to radians
    ang = deg2rad(ang);
    
    % Create polar grid
    [RR, TT] = meshgrid(r, ang);

    % Flip so CW is positive
    TT = -TT;
    
    % Convert to Cartesian
    XX = RR .* sin(TT);
    YY = RR .* cos(TT);
    
    % Plot figure
    figure;
    pcolor(XX, YY, P);
    shading flat
    axis equal
    colormap(parula)
    caxis([0 1])
    xlabel('X')
    ylabel('Y')
    title(sprintf('Scan %d', k))
    colorbar

    % Save to file
    filename = sprintf('Scan_%d.png', k);
    saveas(gcf, fullfile(imageFolder, filename));
end