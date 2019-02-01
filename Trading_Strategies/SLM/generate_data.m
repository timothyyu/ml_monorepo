function [ data ] = generate_data( input ,N)
%   generate the data for training
%   

n = size(input,1)-N+1;
data = zeros(n,1);
for i = 1:n
    d = input.s(i:i+N-1);
    m = [];
    for j = 1:N
        m = [m, num2str(d(j))];
    end
    data(i) = str2double(m);
end


end

%%%%% test