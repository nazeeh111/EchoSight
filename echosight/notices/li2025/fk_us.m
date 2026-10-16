function [dat, depth] = fk_us(s)

    % loading
    offset = s.offset;
    interp_times = s.interp_times;   % interpolation times in raw data
    is_envelope = s.is_envelope;    % if take the envelope
    K=s.K;                % downsample data
    thr_set = s.thr_set;
    color_range = s.color_range;
    dist_range = s.dist_range;
    rect_data = s.rect_data;
    
    % take the envelope
    if is_envelope
        envelope_sig = zeros(size(rect_data,1),size(rect_data,2),size(rect_data,3));
        for i = 1:size(rect_data,1)
            for j = 1:size(rect_data,2)
                [envelope_sig(i,j,:) ,~] = envelope(squeeze(rect_data(i,j,:)));
            end
        end
        rect_data = envelope_sig;
    end
    
    % show signal
    figure
    plot(squeeze(rect_data(round(size(rect_data,1)/2),round(size(rect_data,2)/2),1:offset)))
    grid on;
    box off;
    title('Signal(t)')
    xlabel('Time(us)')
    ylabel('Amplitude(V)')
    
    % Interpolation and downsample
    rect_data = interpolate_data(rect_data,interp_times); 
    for k = 1:K
        rect_data = rect_data(:,:,1:2:end) + rect_data(:,:,2:2:end);
    end
    
    wall_size=0.42;               % size of scan plane
    c = 343;                      % Speed of second
    width = wall_size / 2;
    bin_resolution = 1e-6*2^K;    % bin resolution
    N = size(rect_data,1);        % Spatial resolution of data
    M = size(rect_data,3);        % Temporal resolution of data
    range = M.*c.*bin_resolution; % Maximum range
    
    % Define volume representing voxel distance from wall
    data = permute(rect_data,[3 2 1]);
    grid_z = repmat(linspace(0,1,M)',[1 N N]);
    
    % f-k
    [z,y,x] = ndgrid(-M:M-1,-N:N-1,-N:N-1);
    z = z./M; y = y./N; x = x./N;
    data = data .* grid_z.*2;
    if is_envelope 
    data = sqrt(data);
    end
    
    % Step 1: FFT
    tdata = fftshift(fftn(data,2*size(data)));
    
    % Step 2: Stolt trick
    tvol = interpn(z,y,x,tdata,sqrt(abs((((N.*range)./(M.*width.*4)).^2).*(x.^2+y.^2)+z.^2)),y,x,'linear',0);
    tvol = tvol.*(z > 0);
    tvol = tvol.*abs(z)./max(sqrt(abs((((N.*range)./(M.*width.*4)).^2).*(x.^2+y.^2)+z.^2)),1e-6);
    
    % Step 3: IFFT
    tvol = ifftn(ifftshift(tvol));
    if is_envelope
    tvol = abs(tvol).^2;
    end
    vol = abs(tvol(1:end./2,1:end./2,1:end./2));
    
    tic_z = linspace(0,range./2,size(vol,1));
    tic_y = linspace(width,-width,size(vol,2));
    tic_x = linspace(width,-width,size(vol,3));
    
    vol = permute(vol, [1, 3, 2]);
    vol = flip(vol, 2);
    vol = flip(vol, 3);
    
    % figure
    % imagesc(tic_x,tic_y,squeeze(max((vol),[],1)));
    % hold on;
    % plot([0.1 0.2], [0.16 0.16],'white',"LineWidth",8)
    % text(0.10,0.19,'10 cm',"FontSize",22,"Color",'white')
    % hold off;
    % set(gca,'xtick',[],'ytick',[])
    % set(gca,'FontName','times new roman','FontSize',15,'FontWeight','bold');
    % colormap('gray')
    % axis square
    
    % color the figure
    thr = max(max(max(vol)))/thr_set;
    depth = vol2depth(permute(vol,[2,3,1]),thr,K);
    dat = vol2hsv(vol,thr,K,color_range,dist_range);
end

function vv = vol2hsv(vol,thr,K,color_range,dist_range)
    % thr is the threshold to determine the depth image
    % K is the downsample times
    % color_range is the range of color
    % dist_range is the range of distance in depth
    
    depth = vol2depth(permute(vol,[2,3,1]),thr,K);
    width = 0.21;
    tic_y = linspace(width,-width,size(vol,2));
    tic_x = linspace(width,-width,size(vol,3));
    scale1 =  (min(min(depth)) - dist_range(1)) / (dist_range(2) - dist_range(1));
    scale2 =  (max(max(depth)) - dist_range(1)) / (dist_range(2) - dist_range(1));
    
    %------depth_image-------
    figure
    imagesc(tic_x,tic_y,depth);
    set(gca,'FontName','times new roman','FontSize',15,'FontWeight','bold');
    colorbar;
    caxis([min(min(depth))-.3 max(max(depth))]); 
    set(gca,'xtick',[],'ytick',[])
    axis square
    
    %-------colorbar-------
    % cbar = ones(10,100,3);
    % cbar(:,:,1) = repmat(linspace(color_range(1),color_range(2),100),10,1);
    % figure
    % imshow(hsv2rgb(cbar))
    
    color_rio = color_range(2) - color_range(1);
    vv(:,:,1) = rescale(depth,color_rio*(scale1),color_rio*(scale2));
    vv(:,:,2)= 1;
    vv(:,:,3)= 1.5.*rescale(squeeze(max(vol,[],1)),0,1);
    
    %-------color figure-------
    figure
    imagesc(tic_x,tic_y,hsv2rgb(vv))
    set(gca,'FontName','times new roman','FontSize',15,'FontWeight','bold');
    axis square
    set(gca,'xtick',[],'ytick',[])
    hold on;
    plot([0.1 0.2], [0.16 0.16],'white',"LineWidth",8)
    text(0.10,0.19,'10 cm',"FontSize",22,"Color",'white')
    hold off;
end


function depth = vol2depth(vol, thr, k)
    fs = 1e6/2^k;
    c = 343;
    depth = nan(size(vol, 1), size(vol, 2));
    for i = 1:size(vol, 1)
    for j = 1:size(vol, 2)
        for k = 1:size(vol, 3)
        if vol(i, j, k) > thr
            depth(i, j) = k*c/fs/2;
            break
        end
        end
    end
    end
end

function interp_data = interpolate_data(data,N)
    % scale means interpolation times
    % data is the input data cube
    if N>1 && mod(N,1)==0
        [dim1, dim2, dim3] = size(data);
        [x, y, z] = ndgrid(1:dim1, 1:dim2, 1:dim3);
        [xq, yq, zq] = ndgrid(linspace(1, dim1, dim1*N), ...
            linspace(1, dim2, dim2*N), 1:dim3);
        interp_data = interpn(x, y, z, data, xq, yq, zq, 'cubic');
    else
        interp_data = data;
    end
end
