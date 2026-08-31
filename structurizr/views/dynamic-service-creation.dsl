dynamic hosting.master "ServiceCreation" {

    siteUser -> hosting.cli "Starts service creation command"

    hosting.cli -> hosting.master.api "Requests service creation via REST"

    hosting.master.api -> hosting.master.services "Creates requested service"

    hosting.master.services -> hosting.master.scheduler "Requests service placement"

    hosting.master.scheduler -> hosting.master.resources "Checks resource availability"

    hosting.master.scheduler -> hosting.master.nodes "Checks node capabilities and availability"

    hosting.master.scheduler -> hosting.master.reconciliation "Creates assignment and desired state"

    hosting.master.reconciliation -> hosting.master.agentClient "Sends desired state"

    hosting.master.agentClient -> hosting.webAgent "Sends Web desired state via REST"
    hosting.master.agentClient -> hosting.dnsAgent "Sends DNS desired state via REST"
    hosting.master.agentClient -> hosting.mailAgent "Sends Mail desired state via REST"
    hosting.master.agentClient -> hosting.dbAgent "Sends DB desired state via REST"

    hosting.webAgent -> hosting.master.agentClient "Reports actual state"
    hosting.dnsAgent -> hosting.master.agentClient "Reports actual state"
    hosting.mailAgent -> hosting.master.agentClient "Reports actual state"
    hosting.dbAgent -> hosting.master.agentClient "Reports actual state"

    hosting.master.agentClient -> hosting.master.reconciliation "Processes actual state"

    hosting.master.reconciliation -> hosting.master.services "Updates service state"

    hosting.master.services -> hosting.cli "Returns service information"

    hosting.cli -> siteUser "Shows service status"

    autoLayout lr
}