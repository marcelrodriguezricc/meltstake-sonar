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

    % Initialize objects for total average
    num_scans = numel(sonar.scans);
    P_sum = [];

    % For each scan...
    for k = 1:numel(sonar.scans)
    
        % Get field data
        ang = sonar.scans(k).cw_angles;
        A   = sonar.scans(k).cw_dists;
        B   = sonar.scans(k).ccw_dists;
        
        % Average CW and CCW scans
        P = (A + B) / 2;
    
        % Accumulate for total average
        if isempty(P_sum)
            P_sum = P;
        else
            P_sum = P_sum + P;
        end
    
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

    % Average over all scans
    P_avg = P_sum / num_scans;
    
    r = sonar.range(:)';
    ang = sonar.scans(1).cw_angles;
    ang = deg2rad(ang);
    
    [RR, TT] = meshgrid(r, ang);
    TT = -TT;
    
    XX = RR .* sin(TT);
    YY = RR .* cos(TT);
    
    figure;
    pcolor(XX, YY, P_avg);
    shading flat
    axis equal
    colormap(parula)
    caxis([0 1])
    xlabel('X')
    ylabel('Y')
    title('Average of All Scans')
    colorbar
    
    % Save final average image
    saveas(gcf, fullfile(imageFolder, 'average.png'));

end