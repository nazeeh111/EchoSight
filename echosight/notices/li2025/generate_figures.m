s = struct;

%% -----------------Figure 2-------------------
load('Fig2/2024_2_29_22_26_32641_star_dig_H.mat'); % (thr=4.5), colorrange = [0.0 0.8; 1.1,1.6]
%clearvars data_origin data_origin2; 
s.offset = size(data_origin,3);
s.rect_data = data_origin(:,:,1:s.offset);
s.thr_set = 4.5;
s.color_range = [0.0 0.8];
s.dist_range = [1.1,1.6];

s.interp_times = 0;   % interpolation times in raw data (0 or 2)
s.is_envelope = 1;    % if take the envelope (0 or 1)
s.K = 3;        % downsample data(50kHz: 0,1,2,3; 100kHz: 0,1,2)

% reconstruction
[dat_no_interp_env, dep_dat_no_interp_env] = fk_us(s);

s.is_envelope = 0;
[dat_no_interp_no_env, dep_dat_no_interp_no_env] = fk_us(s);

s.interp_times = 2;   
[dat_interp_no_env, dep_dat_interp_no_env]  = fk_us(s);

%% line cuts trhough the star
figure()
r = 8;
phi = linspace(0,2*pi,45);

xr = int16(r*cos(phi)+37);
yr = int16(r*sin(phi)+11);

M = dep_dat_no_interp_no_env;
sel = M(sub2ind([55,55], yr, xr)) ;
% M(sub2ind([55,55], yr, xr)) = 1.5 ;

plot(sel, '-o')
figure()

r = 8;
phi = linspace(0,2*pi,45);

xr = int16(r*cos(phi)+37);
yr = int16(r*sin(phi)+11);

M = dep_dat_no_interp_env;
sel = M(sub2ind([55,55], yr, xr)) ;
plot(sel, '-o')


figure()

r = 16;
phi = linspace(0,2*pi,90);

xr = int16(r*cos(phi)+37*2);
yr = int16(r*sin(phi)+11*2);

M = dep_dat_interp_no_env;
sel = M(sub2ind([110,110], yr, xr));
plot(sel, '-o')



%% -----------------Figure 3(ab) --------------
MTFS_tot; %MTF 

%% -----------------Figrue 3(c)----------------

files = {
    'Fig3/2024_3_11_21_42_265_star_d1.mat', 4.5;
    'Fig3/2024_3_11_22_47_14530_star_d2.mat', 4.5;
    'Fig3/2024_3_12_11_8_23976_star_d3.mat', 4.5;
    'Fig3/2024_3_12_15_6_13975_star_d4.mat', 4.5;
    'Fig3/2024_3_12_16_51_28342_star_d5.mat', 4.5;
    'Fig3/2024_3_12_19_38_9565_star_d6.mat', 3.5;
    'Fig3/2024_3_12_20_47_49400_star_d7.mat', 4;
    'Fig3/2024_3_13_10_41_46540_star_d8.mat', 4;
    'Fig3/2024_3_13_11_45_35312_star_d9.mat', 4;
    'Fig3/2024_3_13_14_15_1215_star_d11.mat', 2.3
};

offset = 20000; 
for i = 1:size(files, 1)
    load( files{i, 1});
    s.offset = offset;
    s.rect_data = data_origin(:,:,1:s.offset);
    s.thr_set =  files{i, 2};
    [dat_star, ~] = fk_us(s);
    fprintf('Processing file %d: %s\n', i, files{i, 1});
end



%% -----------------Figure 4-------------------

load('Fig4/2024_2_22_16_55_12426_board.mat'); % panel a
s.offset = 12000;
s.rect_data = data_origin(:,:,1:s.offset);
s.thr_set = 4;
s.color_range = [0.0 0.85];
s.dist_range = [1.057,1.1];
s.interp_times = 2; 
s.is_envelope = 0;  
s.K = 3;      

[dat_nlos_board, ~] = fk_us(s);



load('Fig4/2024_2_28_21_49_27584_composed_nlos.mat'); % panel b
s.offset = 10000;
s.rect_data = data_origin(:,:,1:s.offset);
s.thr_set = 6.5;
s.color_range = [0.01 0.9];
s.dist_range = [1.2594,1.3061];
s.interp_times = 2; 
s.is_envelope = 0;  
s.K = 3;      

[dat_dino, ~] = fk_us(s);

%% ----------------Figure 5--------------------

addpath("Fig5\");
generate_figure_5;


