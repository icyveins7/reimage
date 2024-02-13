function data = sendReimageData(data, varargin)
    % Write defaults
    fs = 1.0;
    fc = 0.0;
    nperseg = 128;
    noverlap = 16;
    ipaddr = 'localhost';
    port = 5000;

    % Parse varargin
    if nargin <= 2
        fs = varargin{1};
    end
    if nargin <= 3
        fc = varargin{2};
    end
    if nargin <= 4
        nperseg = varargin{3};
    end
    if nargin <= 5
        noverlap = varargin{4};
    end
    if nargin <= 6
        ipaddr = varargin{5};
    end
    if nargin <= 7
        port = varargin{6};
    end 

    client = tcpclient(ipaddr, port);

    % Note that python's multiprocessing.connection reads/writes
    % with the first 4 bytes specifying the length of the payload

    % Write '4' == 52
    msg = uint8([0, 0, 0, 1, 52]); % we write it in this order which python expects
    client.write(msg);

    % Create the header of the 4 values
    % Cast explicitly to double, then typecast to uint8

    % Same for fc

    % Cast explicitly to int32, then typecast to uint8

    % Same for noverlap

    % Send header



    % Read the type (4 bytes + 1 byte payload always)
    datatype = client.read(5); % we can ignore the size since we know it
    datatype = datatype(5);
    % Read the data (4 bytes + the payload remainder)
    rawbyteslength = client.read(4);
    % must swapbytes to get correct length
    rawbyteslength = swapbytes(typecast(rawbyteslength, 'uint32')); 
    % Read the actual payload
    rawbytes = client.read(rawbyteslength);

    % Cast the data
    if datatype == uint8('0')
        data = typecast(rawbytes, 'single');
    elseif datatype == uint8('1')
        data = typecast(rawbytes, 'double');
    end
    
    data = complex(data(1:2:end), data(2:2:end));

end