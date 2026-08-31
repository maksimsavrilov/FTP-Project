dynamic hosting "NodeRegistration-Web" {

    admin -> hosting.cli "Starts node registration command with parameter --role=web"

    hosting.cli -> hosting.master "Requests node registration"

    hosting.master -> hosting.webAgent "Bootstraps via SSH and starts Web Agent"

    hosting.webAgent -> hosting.master "Registers via REST"

    hosting.master -> hosting.webAgent "Returns Node ID and permanent credentials"

    hosting.webAgent -> hosting.master "Reports node information, capabilities and resources"

    hosting.master -> hosting.database "Creates Worker Node record"

    autoLayout lr
}