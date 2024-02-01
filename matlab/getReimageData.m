function data = getReimageData(varargin)
    if nargin == 0
        ipaddr = 'localhost';
        port = 5000;
    else
        ipaddr = varargin(1);
        port = varargin(2);
    end

    client = tcpclient(ipaddr, port);

    % Note that python's multiprocessing.connection reads/writes
    % with the first 4 bytes specifying the length of the payload

    % Write '2' == 50
    msg = uint8([0, 0, 0, 1, 50]); % we write it in this order which python expects
    client.write(msg);
    
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