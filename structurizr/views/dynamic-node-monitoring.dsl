dynamic hosting "NodeMonitoring" {


    hosting.webAgent -> hosting.master "Sends heartbeat and actual state"

    hosting.master -> hosting.database "Update node heartbeat status"


    autoLayout lr
}