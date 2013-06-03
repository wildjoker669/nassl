
from nassl import SSL_CTX, SSL, BIO, WantReadError, SSLV23, SSL_VERIFY_PEER

DEFAULT_BUFFER_SIZE = 4096


class SslClient:

    def __init__(self, sock=None, sslVersion=SSLV23, sslVerifyLocations=None):
        # A Python socket handles transmission of the data
        self._sock = sock 
        
        # OpenSSL objects
        # SSL_CTX
        self._sslCtx = SSL_CTX(sslVersion)
        if sslVerifyLocations:
            self._sslCtx.load_verify_locations(sslVerifyLocations)
            self._sslCtx.set_verify(SSL_VERIFY_PEER)
        
        # SSL
        self._ssl = SSL(self._sslCtx)
        # Specific servers do not reply to a client hello that is bigger than 255 bytes
        # See http://rt.openssl.org/Ticket/Display.html?id=2771&user=guest&pass=guest
        # So we make the default cipher list smaller (to make the client hello smaller)
        self._ssl.set_cipher_list('HIGH:-aNULL:-eNULL:-3DES:-SRP:-PSK:-CAMELLIA') 
        
        # BIOs
        self._internalBio = BIO()
        self._networkBio = BIO()
        
        # http://www.openssl.org/docs/crypto/BIO_s_bio.html
        BIO.make_bio_pair(self._internalBio, self._networkBio)
        self._ssl.set_bio(self._internalBio)


    def do_handshake(self):
        self._ssl.set_connect_state()
        while True:
            try:
                if self._ssl.do_handshake() == 1:
                    break # Handshake was successful

            except WantReadError:
                # OpenSSL is expecting more data from the peer
                # Send available handshake data to the peer
                lenToRead = self._networkBio.pending()
                while lenToRead:
                    # Get the data from the SSL engine
                    handshakeDataOut = self._networkBio.read(lenToRead)
                    # Send it to the peer
                    self._sock.send(handshakeDataOut)
                    lenToRead = self._networkBio.pending()

                # Recover the peer's encrypted response
                handshakeDataIn = self._sock.recv(DEFAULT_BUFFER_SIZE)
                if len(handshakeDataIn) == 0:
                    raise IOError('Handshake failed: Unexpected EOF')
                # Pass the data to the SSL engine
                self._networkBio.write(handshakeDataIn)


    def set_socket(self):
        pass
    
    def get_socket(self):
        pass


    def read(self, size):
        while True:
            # Receive available encrypted data from the peer
            encData = self._sock.recv(DEFAULT_BUFFER_SIZE)
            # Pass it to the SSL engine
            self._networkBio.write(encData)
            
            try:
                # Try to read the decrypted data
                decData = self._ssl.read(size)
                return decData
            
            except WantReadError:
                # The SSL engine needs more data 
                # before it can decrypt the whole message
                pass
        

    def write(self, data):
        # Pass the cleartext data to the SSL engine
        self._ssl.write(data)
        
        # Recover the corresponding encrypted data
        lenToRead = self._networkBio.pending()
        while lenToRead:
            encData = self._networkBio.read(lenToRead)
            # Send the encrypted data to the peer
            self._sock.send(encData)
            lenToRead = self._networkBio.pending()

        
    def shutdown(self):
        pass

    
    def get_secure_renegotiation_support(self):
        return self._ssl.get_secure_renegotiation_support()
    
    
    def get_current_compression_name(self):
        #TODO: test this
        return self._ssl.get_current_compression_name()
    
    
    def set_verify(self, verifyMode):
        return self._ssl.set_verify(verifyMode)
    
    
    def set_tlsext_host_name(self, nameIndication):
        return self._ssl.set_tlsext_host_name(nameIndication)    
    
    
    def get_peer_certificate(self):
        return self._ssl.get_peer_certificate()

