dynamic hosting "ServiceCreation" {

    siteUser -> hosting.cli "Starts service creation command"

    hosting.cli -> hosting.master "Requests service creation via REST"

    hosting.master -> hosting.webAgent "Sends Web desired state via REST"
    hosting.master -> hosting.dnsAgent "Sends DNS desired state via REST"
    hosting.master -> hosting.mailAgent "Sends Mail desired state via REST"
    hosting.master -> hosting.dbAgent "Sends DB desired state via REST"

    hosting.webAgent -> hosting.master "Reports actual state"
    hosting.dnsAgent -> hosting.master "Reports actual state"
    hosting.mailAgent -> hosting.master "Reports actual state"
    hosting.dbAgent -> hosting.master "Reports actual state"

    hosting.master -> hosting.cli "Returns service information"

    hosting.cli -> siteUser "Shows service status"

    autoLayout lr
}