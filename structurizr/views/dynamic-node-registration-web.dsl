dynamic hosting "NodeRegistration-Web" {

    hosting.webBootstrap -> hosting.webService "Deploys and starts service container with adapter"

    hosting.webBootstrap -> hosting.webAgent "Deploys and starts Agent with shared socket mounted before registration"

    hosting.webAgent -> hosting.webService "Uses shared Unix socket after deployment"

    hosting.webAgent -> hosting.master "Registers via REST/HTTP using its bootstrap credential"

    hosting.master -> hosting.database "Persists the WorkerNode record"

    hosting.master -> hosting.webAgent "Returns the stable Node ID and node-specific credential"

    hosting.webAgent -> hosting.master "Uses the returned credential for heartbeats and status reporting"

    autoLayout lr
}
