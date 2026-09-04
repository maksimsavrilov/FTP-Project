dynamic hosting.master "ServiceCreationInternal" {
    
    hosting.master.api -> hosting.master.services "Creates requested service"
    hosting.master.services -> hosting.master.scheduler "Requests service placement"
    hosting.master.scheduler -> hosting.master.resources "Checks resource availability"
    hosting.master.scheduler -> hosting.master.nodes "Checks node capabilities and availability"
    hosting.master.scheduler -> hosting.master.reconciliation "Creates service assignment and desired state"
    hosting.master.reconciliation -> hosting.master.agentClient "Sends desired state"
    hosting.master.agentClient -> hosting.webAgent "Sends Web desired state via REST"
    hosting.webAgent -> hosting.master.agentClient "Reports actual state"
    hosting.master.agentClient -> hosting.master.reconciliation "Returns actual state"
    hosting.master.reconciliation -> hosting.master.services "Updates service state"

    autoLayout lr
}
