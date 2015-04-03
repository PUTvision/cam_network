__author__ = 'Amin'
from twisted.protocols import basic
from twisted.internet import protocol
from twisted.internet import reactor
from twisted.internet import task

from VSNPacket import VSNPacket
from VSNPacket import VSNPacketToClient


class VSNClient(basic.Int32StringReceiver):

    def __init__(self):
        # parameters
        self._private_parameter = 0

    # callbacks and functions to override

    def connectionMade(self):
        print "Connected to server"
        self.factory.client_connected(self)

    def connectionLost(self, reason):
        print "Disconnected from server" + str(reason)
        self.factory.client_disconnected()

    def stringReceived(self, string):
        packet = VSNPacketToClient()
        packet.unpack_from_receive(string)
        self.factory.client_received_data(packet)

    # additional functions

    def send_packet(self, packet):
        data_packed_as_string = packet.pack_to_send()
        self.sendString(data_packed_as_string)


class VSNClientFactory(protocol.ClientFactory):

    protocol = VSNClient
    # above line is equal to
    #def buildProtocol(self, addr):
    #    p = SimpleClient()
    #    p.factory = self
    #    return p

    def __init__(self):
        self.client = None

    def clientConnectionLost(self, connector, reason):
        print "Disconnected, trying to reconnect"
        connector.connect()

    def clientConnectionFailed(self, connector, reason):
        print "Connection failed:", + str(reason)
        reactor.stop()

    def client_connected(self, client):
        self.client = client

    def client_disconnected(self):
        self.client = None

    def client_received_data(self, packet):
        print "Received packet: ", packet.activation_neighbours, ", ", packet.image_type

    def send_packet(self, packet):
        if self.client:
            self.client.send_packet(packet)


def send_packet(packet):
    client_factory.send_packet(packet)

if __name__ == '__main__':
    # constant definitions
    #SERVER_IP = '192.168.0.100'
    SERVER_IP = '127.0.0.1'
    SERVER_PORT = 50001

    # create factory protocol and application
    client_factory = VSNClientFactory()

    # connect factory to this host and port
    reactor.connectTCP(SERVER_IP, SERVER_PORT, client_factory)

    periodic_action = None
    VSN_packet = VSNPacket()
    VSN_packet.set(0, 2.0, 4.0)
    periodic_action = task.LoopingCall(send_packet, VSN_packet)
    periodic_action.start(2.0)
    #self.periodic_action.stop()

    reactor.run()