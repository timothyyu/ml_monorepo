%%data processing
[~,~,data] = xlsread('index_shanghai.csv');
data = cell2table(data(2:end,:),'VariableNames',data(1,:));
% Ret = tick2ret(data(:,2:end));% return


N = 6;

%turn the close price set into categorical variables
s = tick2ret(data.close);
data.s = [0; s];
data.s(data.s>=0) = 2;%price going up
data.s(data.s<0) = 1;%price going down
data.dn = datenum(data.date,'yyyy/mm/dd');
x = generate_data(data,N);
data.x = zeros(size(data,1),1);
data.x(N:end) = x;


%time periods for training
sdate = datenum('19950103','yyyymmdd');
edate = datenum('20041231','yyyymmdd');
tsdate = datenum('20050104','yyyymmdd');
tedate = datenum('20131213','yyyymmdd');

si = find(data.dn == sdate);
ei = find(data.dn == edate);
tsi = find(data.dn == tsdate);
tei = find(data.dn == tedate);

test = data(tsi:tei,:);
train_x = data.x(si:ei);
train_x = train_x(7:end);
test_x = data.x(tsi:tei);

pre = zeros(size(test_x,1),2);%the predict for everyday
pre(:,1) = test.dn;

%% backtesting
%position
Pos = zeros(size(pre,1),1);
%daily return 
ReturnD = zeros(size(pre,1),1);
%trading happend in that day
trading = ones(size(pre,1),1);
trading(1) = 0;

%open price
Open = zeros(size(pre,1),1);
TradingCost = 0.0001;
Stop = 0.01;
for d = 2:length(test_x)-1
    %train_x(end+1) = test_x(d);
    pro = [unique(train_x),hist(train_x,unique(train_x))'/length(train_x)];
    
    for i =1:2:size(pro,1)
        if ((test.x(d+1)==pro(i+1,1))|| (test.x(d+1)==pro(i,1)))&&(pro(i+1,2)> pro(i,2))
            pre(d,2) = 1;
            break;
        end
    end
    
    %buy
    if pre(d,2)==1
        if Pos(d-1) == 0
            Pos(d) = 1;
            Open(d) = test.close(d);
            %ReturnD(d)=-TradingCost/(1+TradingCost);
        end

        if Pos(d-1) == -1
            if test.high(d)>=(1+Stop)*Open(d-1)
                Pos(d) = 1;
                Open(d) = test.close(d);
                ReturnD(d)=-Stop-(2+Stop)*TradingCost;
            else
                Pos(d) = 1;
                Open(d) = test.close(d);
                ReturnD(d)=1-TradingCost-test.close(d)*(1+TradingCost)/Open(d-1);
            end
        end

        if Pos(d-1) == 1
            if test.low(d)<=(1-Stop)*Open(d-1)
                Pos(d) = 1;
                Open(d) = test.close(d);
                ReturnD(d) = -Stop-(2-Stop)*TradingCost;
            else
                Pos(d) = 1;
                Open(d) = Open(d-1);
                trading(d) = 0;
            end
                
        end
    %sell
    else 
        if Pos(d-1) == 0
            Pos(d) = -1;
            Open(d) = test.close(d);
            %ReturnD(d)=-TradingCost;
        elseif Pos(d-1) == 1
            if test.low(d)<=(1-Stop)*Open(d-1)
                Pos(d) = -1;
                Open(d) = test.close(d);
                ReturnD(d)= -Stop-(2-Stop)*TradingCost;
            else
                Pos(d) = -1;
                Open(d) = test.close(d);
                ReturnD(d) = test.close(d)*(1-TradingCost)/Open(d-1)-TradingCost-1;
                
            end
        else
            if test.high(d)>=(1+Stop)*Open(d-1)
                Pos(d) = -1;
                Open(d) = test.close(d);
                ReturnD(d) = -Stop-(2+Stop)*TradingCost;
            else
                Pos(d) = -1;
                Open(d) = Open(d-1);
                trading(d) = 0;
            end
        end
    end
    
end

%sell all position at last day
if Pos(end-1)==1
    ReturnD(end) = (test.close(end)-Open(end-1))/Open(end-1);
else
    ReturnD(end) = (Open(end-1)-test.close(end))/Open(end-1);
end

%%
CumRet = cumprod((1+ReturnD))-1;% cumulative return        
Cum_index = cumprod((1+tick2ret(test.close)))-1;
plot([CumRet(2:end),Cum_index])
title('考虑止损下SLM择时交易累计收益');
legend('考虑止损下策略收益','上证指数收益')
%% max drawdown
MaxDrawD = zeros(size(CumRet,1),1);
for t = 1:size(CumRet,1)
    C = max( CumRet(1:t,1)+1 );
    if C == CumRet(t)+1
        MaxDrawD(t) = 0;
    else
        MaxDrawD(t) = (CumRet(t)-C+1)/C;
    end
end
MaxDrawD = abs(MaxDrawD);
%%
CumRet(:,2) = str2num(datestr(test.dn,'yyyy'));
y = unique(CumRet(:,2));
CumRet_year = y;
num_win = y;
num_trade = y;
avg = y;
md = [];
for i = 1:length(y)
    l = cumprod((1+ReturnD(CumRet(:,2)==y(i))))-1;
    CumRet_year(i,2) = l(end);
    
    l = trading(CumRet(:,2)==y(i));
    num_trade(i,2) = sum(l);
    
       
    l = ReturnD(CumRet(:,2)==y(i));
    avg(i,2) = mean(l(l~=0));
    avg(i,3) = mean(l(l>0));
    avg(i,4) = mean(l(l<0));
    l(l>0) = 1;
    l(l~=1)=0;
    num_win(i,2) = sum(l);
    
    md(i) = -max(MaxDrawD(CumRet(:,2)==y(i)));
       
end

num_win(:,3) = num_win(:,2)./num_trade(:,2);


%% graph
figure;
subplot(2,1,1);
plot(CumRet(:,1));
grid on;
axis tight;
title(['收益曲线'],'FontWeight', 'Bold');
set(gca,'XTick',linspace(1,length(test.date),10));  
set(gca,'XTickLabel',test.date(floor(linspace(1,length(test.date),10))',:));
hold on;
plot(Cum_index,'r');
leg=legend('策略收益','上证指数收益');
set(leg,'location','NorthWest','FontSize',8);


subplot(2,1,2);
plot(-MaxDrawD);
grid on;
axis tight;
title(['历史最大回撤：',num2str(max(MaxDrawD))],'FontWeight', 'Bold');
set(gca,'XTick',linspace(1,length(test.date),10));  
set(gca,'XTickLabel',test.date(floor(linspace(1,length(test.date),10))',:));
hold on;
plot(Cum_index,'r');
leg=legend('策略回撤','上证指数收益');
set(leg,'location','NorthWest','FontSize',8);

%% Report

Report = [[0,0;0,CumRet(end,1)],CumRet_year'];
Report(3,:) = [0,sum(num_trade(:,2)),num_trade(:,2)'];
Report(4:5,:) = [[0;0],[sum(num_win(:,2));mean(num_win(:,3))],num_win(:,2:3)'];
Report(6:8,:) = [[0;0;0],mean(avg(:,2:4))',avg(:,2:4)'];
Report(9,:) = [0,-max(MaxDrawD),md];
Report = num2cell(Report);
name = {'评价指标';'收益率';'交易次数';'获胜次数';'胜率';'单次均收益率';'单次获胜均收益率';'单次失败均收益率';'最大回撤'};
for i =1:length(name)
    Report(i,1) = name(i);
end

Report