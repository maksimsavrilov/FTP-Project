dynamic hosting "NodeRegistration-Db" {

    admin -> hosting.cli "Starts node registration command with parameter --role=db"

    hosting.cli -> hosting.master "Requests node registration"

    hosting.master -> hosting.dbAgent "Bootstraps via SSH and starts Db Agent"

    hosting.dbAgent -> hosting.master "Registers via REST"

    hosting.master -> hosting.dbAgent "Returns Node ID and permanent credentials"

    hosting.dbAgent -> hosting.master "Reports node information, capabilities and resources"

    hosting.master -> hosting.database "Creates Worker Node record"

    autoLayout lr
}