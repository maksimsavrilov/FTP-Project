dynamic hosting "NodeRegistration-Db" {

    hosting.dbAgent -> hosting.master "Registers via REST/HTTP using its bootstrap credential"

    hosting.master -> hosting.database "Persists the WorkerNode record"

    hosting.master -> hosting.dbAgent "Returns the stable Node ID and node-specific credential"

    hosting.dbAgent -> hosting.master "Uses the returned credential for heartbeats and status reporting"

    autoLayout lr
}