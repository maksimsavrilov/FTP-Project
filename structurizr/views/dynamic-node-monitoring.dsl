dynamic hosting "NodeMonitoring" {
    hosting.webAgent -> hosting.master "Sends heartbeat and actual state"
    hosting.dnsAgent -> hosting.master "Sends heartbeat and actual state"
    hosting.mailAgent -> hosting.master "Sends heartbeat and actual state"
    hosting.dbAgent -> hosting.master "Sends heartbeat and actual state"
    
    hosting.master -> hosting.database "Updates node heartbeat and observed state"

    autoLayout lr
}