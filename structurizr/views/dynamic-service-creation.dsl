dynamic hosting "WebServiceCreation" {

    siteUser -> hosting.cli "Starts service creation command"

    hosting.cli -> hosting.master "Requests service creation via REST"

    hosting.master -> hosting.database "Persists service, assignment and desired state"

    hosting.master -> hosting.webAgent "Sends Web service desired state via REST"
    hosting.webAgent -> hosting.master "Reports Web service actual state via REST"
    hosting.master -> hosting.cli "Returns service information"

    hosting.cli -> siteUser "Shows service status"

    autoLayout lr
}