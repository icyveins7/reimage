function sendReimageData(data, varargin)
    % Write defaults
    fs = 1.0;
    fc = 0.0;
    nperseg = 128;
    noverlap = 16;
    ipaddr = 'localhost';
    port = 5000;

    % Parse varargin
    if length(varargin) >= 1 
        if size(varargin) <= 2
            fs = varargin{1};
        end
        if size(varargin) <= 3
            fc = varargin{2};
        end
        if size(varargin) <= 4
            nperseg = varargin{3};
        end
        if size(varargin) <= 5
            noverlap = varargin{4};
        end
        if size(varargin) <= 6
            ipaddr = varargin{5};
        end
        if size(varargin) <= 7
            port = varargin{6};
        end 
    end

    client = tcpclient(ipaddr, port);

    % Note that python's multiprocessing.connection reads/writes
    % with the first 4 bytes specifying the length of the payload

    % Write '4' == 52
    msg = uint8([0, 0, 0, 1, 52]); % we write it in this order which python expects
    client.write(msg);

    % Create the header of the 4 values, 24 bytes
    header = uint8([0,0,0,24]);
    % Cast explicitly to double, then typecast to uint8
    header = [header typecast(double(fs), 'uint8')];
    % Same for fc
    header = [header typecast(double(fc), 'uint8')];
    % Cast explicitly to int32, then typecast to uint8
    header = [header typecast(int32(nperseg), 'uint8')];
    % Same for noverlap
    header = [header typecast(int32(noverlap), 'uint8')];
    % Send header
    client.write(header);

    % Send actual data
    % Cast as complex singles
    % Matlab has no typecast for complex arrays, so we have to extract and reshape
    cdata = reshape([real(data); imag(data)], 1, []); % First into row vector
    cdata = single(cdata); % Then cast to single
    cdata = typecast(cdata, 'uint8');
    cdatalength = typecast(swapbytes(uint32([length(cdata)])), 'uint8');
    % Send it
    sdata = [cdatalength cdata];
    client.write(sdata);

end