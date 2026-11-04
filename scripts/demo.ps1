param(
    [ValidateSet('Preparar','Entrenar','Desplegar','Monitorear','Probar','Escalar','Limpiar')]
    [string]$Etapa = 'Probar',
    [ValidateRange(1,8)][int]$Replicas = 5
)
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$repoProyecto = (Get-Location).Path
$salidasProyecto = Join-Path $repoProyecto 'salidas'
New-Item -ItemType Directory -Force $salidasProyecto | Out-Null
function Ejecutar([string]$Programa, [string[]]$Argumentos) {
    & $Programa @Argumentos
    if ($LASTEXITCODE -ne 0) { throw "$Programa termino con codigo $LASTEXITCODE" }
}
if ((kubectl config current-context) -ne 'docker-desktop') {
    throw 'Selecciona el cluster local docker-desktop antes de ejecutar la demostracion.'
}
switch ($Etapa) {
    'Preparar' {
        Ejecutar docker @('build','-t','credito-mlops:1.3','.')
        Ejecutar kubectl @('--context','docker-desktop','apply','-f','k8s/01-mlflow.yaml')
        Ejecutar kubectl @('-n','credito-mlops','rollout','status','deployment/mlflow','--timeout=240s')
    }
    'Entrenar' {
        $revisionProyecto = (git rev-parse HEAD).Trim()
        Ejecutar docker @('run','--rm','-e','MLFLOW_TRACKING_URI=http://host.docker.internal:30500',
            '-e',"GIT_COMMIT=$revisionProyecto",'-e','SALIDA=/salidas',
            '--mount',"type=bind,source=$salidasProyecto,target=/salidas",'credito-mlops:1.3','python','-m','src.entrenar')
    }
    'Desplegar' {
        Ejecutar kubectl @('apply','-f','k8s/02-api.yaml')
        Ejecutar kubectl @('-n','credito-mlops','rollout','status','deployment/credito-api','--timeout=240s')
        Write-Host 'Interfaz: http://localhost:30081  |  MLflow: http://localhost:30500'
    }
    'Monitorear' {
        Ejecutar docker @('run','--rm','-e','MLFLOW_TRACKING_URI=http://host.docker.internal:30500',
            '-e','SALIDA=/salidas','--mount',"type=bind,source=$salidasProyecto,target=/salidas",
            'credito-mlops:1.3','python','-m','src.drift')
        foreach ($loteProyecto in @('normal','derivado')) {
            & docker run --rm --mount "type=bind,source=$salidasProyecto,target=/salidas,readonly" credito-mlops:1.3 python -m src.drift --baseline /salidas/baseline.csv --lote "/salidas/lote_$loteProyecto.csv"
            $esperadoProyecto = if ($loteProyecto -eq 'derivado') { 2 } else { 0 }
            if ($LASTEXITCODE -ne $esperadoProyecto) { throw "Resultado inesperado en lote $loteProyecto" }
            Write-Host "Lote $loteProyecto : codigo esperado $esperadoProyecto"
        }
    }
    'Probar' {
        Ejecutar docker @('run','--rm','credito-mlops:1.3','python','-m','pytest','-q','-p','no:cacheprovider','--disable-warnings')
        $respuestasProyecto = 1..20 | ForEach-Object {
            Invoke-RestMethod http://localhost:30081/health -Headers @{Connection='close'}
        }
        $respuestasProyecto | Group-Object pod | Select-Object Count,Name | Format-Table
        Ejecutar kubectl @('-n','credito-mlops','get','pods','-o','wide')
    }
    'Escalar' {
        Ejecutar kubectl @('-n','credito-mlops','scale','deployment/credito-api',"--replicas=$Replicas")
        Ejecutar kubectl @('-n','credito-mlops','rollout','status','deployment/credito-api','--timeout=240s')
        Ejecutar kubectl @('-n','credito-mlops','get','pods','-l','app=credito-api')
    }
    'Limpiar' {
        # Elimina solamente los recursos del proyecto, incluido su registro persistente.
        Ejecutar kubectl @('--context','docker-desktop','delete','namespace','credito-mlops','--ignore-not-found')
    }
}
