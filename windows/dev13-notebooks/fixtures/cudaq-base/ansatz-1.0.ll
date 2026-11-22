; ModuleID = 'LLVMDialectModule'
source_filename = "LLVMDialectModule"
target datalayout = "e-m:e-p270:32:32-p271:32:32-p272:64:64-i64:64-i128:128-f80:128-n8:16:32:64-S128"

define void @__nvqpp__mlirgen__ansatz..0x79bd35081460(double %0) #0 {
  call void @__quantum__qis__x__body(ptr null)
  call void @__quantum__qis__ry__body(double 5.900000e-01, ptr inttoptr (i64 1 to ptr))
  call void @__quantum__qis__cnot__body(ptr inttoptr (i64 1 to ptr), ptr null)
  ret void
}

declare void @__quantum__qis__x__body(ptr)

declare void @__quantum__qis__ry__body(double, ptr)

declare void @__quantum__qis__cnot__body(ptr, ptr)

attributes #0 = { "entry_point" "output_labeling_schema"="schema_id" "qir_profiles"="base_profile" "required_num_qubits"="2" }

!llvm.module.flags = !{!0}

!0 = !{i32 2, !"Debug Info Version", i32 3}
