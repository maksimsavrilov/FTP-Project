dynamic hosting "NodeRegistration-Web" {

    hosting.webAgent -> hosting.master "Registers via REST/HTTP using its bootstrap credential"

    hosting.master -> hosting.database "Persists the WorkerNode record"

    hosting.master -> hosting.webAgent "Returns the stable Node ID and node-specific credential"

    hosting.webAgent -> hosting.master "Uses the returned credential for heartbeats and status reporting"

    autoLayout lr
}